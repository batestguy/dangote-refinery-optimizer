"""Blend-quality model tests — LBI helpers, hand-computed pool qualities,
spec-violation detection, and slate-level behavior."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dangote_opt.config import CONFIG
from dangote_opt.data.assays import frame_to_records
from dangote_opt.features.bridge import component_volumes
from dangote_opt.features.quality import (
    CRUDE_QUALITIES,
    UNIT_QUALITIES,
    blend_pool_qualities,
    linear_blend,
    pool_qualities,
    quality_violation_magnitude,
    quality_violations,
    rvp_from_index,
    rvp_index,
)

SLATE_PARQUET = "data/derived/slate_phase1.parquet"


@pytest.fixture(scope="module")
def slate():
    return frame_to_records(pd.read_parquet(SLATE_PARQUET))


def synthetic_curve() -> np.ndarray:
    """Anchored at 15 °C: light nap 10%, nap 30%, kero 15%, diesel 25%, VGO 23%."""
    temps = [15, 80, 180, 260, 360, 540, 600]
    vols = [0, 10, 30, 45, 70, 93, 96]
    return np.array(list(zip(temps, vols, strict=True)), dtype=float)


def test_rvp_index_roundtrip():
    kpa = 45.0
    assert rvp_from_index(float(rvp_index(np.array([kpa]))[0])) == pytest.approx(kpa)


def test_rvp_index_is_1_25_power():
    assert float(rvp_index(np.array([2.0]))[0]) == pytest.approx(2.0**1.25)


def test_pool_qualities_hand_computed():
    """Every volume below comes from the bridge constants; RON is plain arithmetic."""
    curve = synthetic_curve()
    comp = component_volumes(curve, severity=0.0)
    q = CRUDE_QUALITIES["bonny_light"]  # light_naphtha_ron 77.2
    pq = pool_qualities(comp, q)

    # Gasoline streams at severity 0 (hand-derived from bridge constants):
    # isomerate 0.075, reformate 0.17, fcc gasoline 0.046, alkylate 0.01472
    vols = np.array([comp[s] for s in ("isomerate", "reformate", "fcc_gasoline", "alkylate")])
    assert vols[0] == pytest.approx(0.075)
    assert vols[1] == pytest.approx(0.20 * 0.85)
    rons = np.array([q.light_naphtha_ron + 4.0, 98.0, 93.0, 93.0])
    assert pq["gasoline_ron"] == pytest.approx(float(np.dot(rons, vols) / vols.sum()))
    # RVP: same volumes through the psi^1.25 index (roundtrip identity)
    rvps = np.array(
        [UNIT_QUALITIES[s].rvp_kpa for s in ("isomerate", "reformate", "fcc_gasoline", "alkylate")]
    )
    assert pq["gasoline_rvp_kpa"] == pytest.approx(
        rvp_from_index(float(np.dot(rvp_index(rvps), vols) / vols.sum()))
    )
    # Diesel: SR cut @ published cetane + LCO @ 22
    expected_cetane = (comp["sr_distillate"] * q.sr_distillate_cetane + comp["fcc_lco"] * 22.0) / (
        comp["sr_distillate"] + comp["fcc_lco"]
    )
    assert pq["diesel_cetane_idx"] == pytest.approx(expected_cetane)
    # Jet: single-component pool → the crude's kero freeze point
    assert pq["jet_freeze_c"] == q.kero_freeze_c


def test_severity_raises_ron_and_lowers_cetane(slate):
    """More FCC severity → more low-RVP/high-RON FCC gasoline in the pool, but
    more low-cetane LCO in diesel — both monotone (methodology §3c)."""
    r = slate[0]
    curve = np.array(r.tbp_curve)
    ones = np.array([1.0])
    q0 = blend_pool_qualities(ones, [curve], [CRUDE_QUALITIES[r.crude_id]], 0.0)
    q1 = blend_pool_qualities(ones, [curve], [CRUDE_QUALITIES[r.crude_id]], 1.0)
    assert q1["gasoline_ron"] > q0["gasoline_ron"]
    assert q1["diesel_cetane_idx"] < q0["diesel_cetane_idx"]


def test_slate_equal_weight_passes_all_specs(slate):
    curves = [np.array(r.tbp_curve, dtype=float) for r in slate]
    quals = [CRUDE_QUALITIES[r.crude_id] for r in slate]
    q = blend_pool_qualities(np.full(5, 0.2), curves, quals, 0.5)
    assert quality_violations(q) == []
    assert 91 <= q["gasoline_ron"] <= 96
    assert q["gasoline_rvp_kpa"] < 45
    assert q["jet_freeze_c"] <= CONFIG.jet_freeze_point_c_max
    assert q["diesel_cetane_idx"] >= CONFIG.diesel_cetane_min


def test_all_slate_quality_records_document_provenance(slate):
    for r in slate:
        q = CRUDE_QUALITIES[r.crude_id]
        for status in (q.ron_status, q.freeze_status, q.cetane_status):
            assert "PUBLISHED" in status or "ASSUMED" in status


def test_quality_violations_flag_each_spec():
    on_spec = {
        "gasoline_ron": 93.0,
        "gasoline_rvp_kpa": 40.0,
        "jet_freeze_c": -50.0,
        "diesel_cetane_idx": 47.0,
    }
    assert quality_violations(on_spec) == []

    off = dict(on_spec, gasoline_ron=89.5)
    assert any("RON" in v for v in quality_violations(off))
    off = dict(on_spec, gasoline_rvp_kpa=61.0)
    assert any("RVP" in v for v in quality_violations(off))
    off = dict(on_spec, jet_freeze_c=-46.0)
    assert any("freeze" in v for v in quality_violations(off))
    off = dict(on_spec, diesel_cetane_idx=44.0)
    assert any("cetane" in v for v in quality_violations(off))


def test_quality_violation_magnitude_linear_plus_quadratic():
    quals = {
        "gasoline_ron": 90.0,  # 1.0 under spec
        "gasoline_rvp_kpa": 40.0,
        "jet_freeze_c": -50.0,
        "diesel_cetane_idx": 47.0,
    }
    assert quality_violation_magnitude(quals) == pytest.approx(1.0 + 1.0**2)


def test_linear_blend_requires_volume():
    with pytest.raises(ValueError, match="zero volume"):
        linear_blend(np.array([90.0]), np.array([0.0]))


def test_blend_pool_qualities_empty_gasoline_raises():
    # No naphtha AND no VGO (so no FCC gasoline) → empty gasoline pool,
    # while kero/diesel pools stay non-empty.
    curve = np.array([[15, 0], [180, 0], [260, 20], [360, 60], [361, 60], [600, 60]], dtype=float)
    with pytest.raises(ValueError, match="gasoline pool"):
        blend_pool_qualities(np.array([1.0]), [curve], [CRUDE_QUALITIES["bonny_light"]], 0.5)


def test_blend_pool_qualities_single_crude_matches_pool_qualities():
    """Blend-level stream aggregation must agree with the per-crude helper."""
    curve = synthetic_curve()
    q_ref = CRUDE_QUALITIES["bonny_light"]
    per_crude = pool_qualities(component_volumes(curve, 0.5), q_ref)
    blended = blend_pool_qualities(np.array([1.0]), [curve], [q_ref], 0.5)
    for k in per_crude:
        assert blended[k] == pytest.approx(per_crude[k])
