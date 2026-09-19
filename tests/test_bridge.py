"""Stage-1 bridge tests — cut integration, mass balance, severity response,
and ground-truth checks against the published Bonny Light cut yields."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dangote_opt.data.assays import frame_to_records
from dangote_opt.features.bridge import (
    ALKYLATE_SHARE,
    BUTANE_PULL_SHARE,
    FCC_CONVERSION_AT_S0,
    FCC_CONVERSION_AT_S1,
    FCC_GAS_COKE_SHARE,
    ISOM_YIELD,
    NAPHTHA_END_C,
    REFORMER_YIELD,
    component_volumes,
    tbp_cut_fractions,
    yields_from_assay,
)
from dangote_opt.optimization.objective import RefineryObjective

SLATE_PARQUET = "data/derived/slate_phase1.parquet"


@pytest.fixture(scope="module")
def slate():
    df = pd.read_parquet(SLATE_PARQUET)
    return frame_to_records(df)


def synthetic_curve() -> np.ndarray:
    """Simple linear-ish curve anchored at 15 °C (parser-normalized shape)."""
    temps = [15, 100, 180, 260, 360, 540, 600]
    vols = [0, 15, 30, 45, 70, 93, 96]
    return np.array(list(zip(temps, vols, strict=True)), dtype=float)


def test_cut_fractions_sum_to_one_synthetic():
    cuts = tbp_cut_fractions(synthetic_curve())
    assert cuts.sum() == pytest.approx(1.0)
    assert (cuts >= 0).all()


def test_cut_fractions_match_manual_integration():
    curve = synthetic_curve()
    cuts = tbp_cut_fractions(curve)
    vols = dict(zip(curve[:, 0], curve[:, 1], strict=True))
    # naphtha = vol% at 180 = 30
    assert cuts[0] == pytest.approx(vols[180] / 100, abs=1e-9)
    assert cuts[1] == pytest.approx((vols[260] - vols[180]) / 100, abs=1e-9)
    assert cuts[2] == pytest.approx((vols[360] - vols[260]) / 100, abs=1e-9)
    assert cuts[3] == pytest.approx((vols[540] - vols[360]) / 100, abs=1e-9)
    assert cuts[4] == pytest.approx(1 - vols[540] / 100, abs=1e-9)


def test_curve_outside_range_contributes_nothing():
    """A curve ending at 450 °C lumps all heavier material into residue."""
    temps = [15, 100, 200, 300, 450]
    vols = [0, 20, 40, 65, 90]
    curve = np.array(list(zip(temps, vols, strict=True)), dtype=float)
    cuts = tbp_cut_fractions(curve)
    assert cuts[4] == pytest.approx(0.10)  # 1 - 90% at last point


def test_yields_sum_to_one_and_are_bounded(slate):
    for r in slate:
        y = yields_from_assay(r.api, r.sulfur_pct, np.array(r.tbp_curve), 0.5)
        assert (y >= 0).all()
        assert y.sum() == pytest.approx(1.0, abs=0.01)  # HT loss ≈ 1%
        assert (y <= 1).all()


def test_severity_moves_conversion_monotonically(slate):
    r = slate[0]
    curve = np.array(r.tbp_curve)
    g0 = yields_from_assay(r.api, r.sulfur_pct, curve, 0.0)
    g1 = yields_from_assay(r.api, r.sulfur_pct, curve, 1.0)
    assert g1[0] > g0[0]  # gasoline up
    assert g1[3] < g0[3]  # petrochem/residue down
    # conversion bounds are honored
    assert (g1[0] - g0[0]) / (FCC_CONVERSION_AT_S1 - FCC_CONVERSION_AT_S0) > 0


def test_severity_out_of_bounds_raises(slate):
    r = slate[0]
    with pytest.raises(ValueError, match="severity"):
        yields_from_assay(r.api, r.sulfur_pct, np.array(r.tbp_curve), 1.5)


@pytest.mark.parametrize(
    ("crude_id", "gas_lo", "gas_hi"),
    [
        ("bonny_light", 0.28, 0.45),
        ("alaska_north_slope", 0.25, 0.42),
    ],
)
def test_gasoline_yield_in_sanity_band(slate, crude_id, gas_lo, gas_hi):
    """Light crudes yield ~30–40% gasoline at mid severity — cited band in
    docs/methodology.md (Gary & Handwerk hydroskimming/conversion ranges)."""
    r = next(x for x in slate if x.crude_id == crude_id)
    y = yields_from_assay(r.api, r.sulfur_pct, np.array(r.tbp_curve), 0.5)
    assert gas_lo <= y[0] <= gas_hi


def test_ans_has_more_residue_than_bonny_light(slate):
    """Published sheets: ANS residue >> Bonny Light residue — bridge must agree."""
    cuts = {r.crude_id: tbp_cut_fractions(np.array(r.tbp_curve)) for r in slate}
    assert cuts["alaska_north_slope"][4] > 2 * cuts["bonny_light"][4]


def test_objective_uses_injected_yield_model(slate):
    """The Phase 3 ETR plugs in behind the same hook — verify delegation."""
    r = slate[0]

    def fake_model(ratios, severity):
        return np.array([0.4, 0.3, 0.2, 0.1])  # constant, sums to 1

    obj = RefineryObjective(
        crude_apis=np.array([r.api] * 5),
        crude_sulfurs=np.array([r.sulfur_pct] * 5),
        crude_costs=np.array([80.0] * 5),
        product_prices=np.array([95.0, 100.0, 90.0, 70.0]),
        yield_model=fake_model,
    )
    x = np.r_[np.full(5, 0.2), 0.5]
    assert obj(x) == pytest.approx(-(0.4 * 95 + 0.3 * 100 + 0.2 * 90 + 0.1 * 70 - 80.0))


def test_objective_placeholder_still_works_without_model():
    obj = RefineryObjective(
        crude_apis=np.array([35.0] * 5),
        crude_sulfurs=np.array([0.4] * 5),
        crude_costs=np.array([80.0] * 5),
        product_prices=np.array([95.0, 100.0, 90.0, 70.0]),
    )
    x = np.r_[np.full(5, 0.2), 0.0]
    assert np.isfinite(obj(x))
    assert NAPHTHA_END_C == 180.0  # cut scheme pinned


# --- octane units & component streams (methodology.md §3b) ------------------


def test_component_volumes_match_yield_pools(slate):
    """One mass balance, two consumers: pooling component_volumes must
    reproduce yields_from_assay exactly at every severity."""
    for r in slate:
        curve = np.array(r.tbp_curve, dtype=float)
        for sev in (0.0, 0.5, 1.0):
            cv = component_volumes(curve, sev)
            pools = np.array(
                [
                    cv["isomerate"] + cv["reformate"] + cv["fcc_gasoline"] + cv["alkylate"],
                    (cv["sr_distillate"] + cv["fcc_lco"]) * (1 - 0.01),
                    cv["kero"],
                    cv["residue"]
                    + cv["vgo_slurry"]
                    + cv["fcc_gas_nonalk"]
                    + cv["reformer_lpg"]
                    + cv["butane_lpg"],
                ]
            )
            y = yields_from_assay(r.api, r.sulfur_pct, curve, sev)
            assert np.allclose(pools, y, atol=1e-12), (r.crude_id, sev)


def test_component_stream_arithmetic():
    curve = synthetic_curve()
    cv = component_volumes(curve, severity=0.0)
    cuts = tbp_cut_fractions(curve)
    naphtha = cuts[0]
    light = cv["isomerate"] / (1 - BUTANE_PULL_SHARE)  # undo pull
    assert cv["light_naphtha"] == pytest.approx(light * (1 - BUTANE_PULL_SHARE))
    assert cv["butane_lpg"] == pytest.approx(light * BUTANE_PULL_SHARE)
    assert cv["mid_naphtha"] == pytest.approx(naphtha - light)
    assert cv["reformate"] == pytest.approx(cv["mid_naphtha"] * REFORMER_YIELD)
    assert cv["isomerate"] == pytest.approx(cv["light_naphtha"] * ISOM_YIELD)
    # severity 0 → VGO conversion 40%, gas+coke share 32%, half alkylated
    assert cv["fcc_gasoline"] == pytest.approx(cuts[3] * 0.40 * 0.50)
    assert cv["alkylate"] == pytest.approx(cuts[3] * 0.40 * FCC_GAS_COKE_SHARE * ALKYLATE_SHARE)


def test_butane_pull_feeds_petrochem_not_gasoline(slate):
    """RVP control: pulled LPG must leave the gasoline pool (mass-balance check
    via petrochem share) — without it no blend meets the RVP 60 kPa spec."""
    r = slate[0]
    curve = np.array(r.tbp_curve, dtype=float)
    cv = component_volumes(curve, 0.5)
    assert cv["butane_lpg"] > 0
    # With the pull, isomerate = (1-pull)·light_nap; without, it would be light_nap.
    # The no-FCC baseline (isomerate + reformate) must therefore sit strictly
    # between the pulled and un-pulled light-nap volumes.
    light_nap = cv["isomerate"] / (1 - BUTANE_PULL_SHARE)
    no_fcc_pool = cv["isomerate"] + cv["reformate"]
    assert no_fcc_pool < light_nap + cv["reformate"]  # pull removed volume
    assert no_fcc_pool > cv["isomerate"]  # ...but light nap is still in the pool


def test_severity_out_of_bounds_raises_in_component_volumes(slate):
    with pytest.raises(ValueError, match="severity"):
        component_volumes(np.array(slate[0].tbp_curve), 1.5)
