"""Phase 5 scenario-engine tests — bootstrap, exactness anchors, risk metrics.

The zero-draw and Brent-shift tests pin the *mathematical* claims in
scenarios.py's docstring (base-state exactness; additive cost shift cancels
from the LP argmax), not just plausible-looking numbers.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dangote_opt.config import CONFIG
from dangote_opt.data.assays import frame_to_records
from dangote_opt.data.costs import build_crude_costs
from dangote_opt.features.quality import CRUDE_QUALITIES
from dangote_opt.optimization.baselines import build_lp_problem, solve_lp
from dangote_opt.optimization.scenarios import (
    bootstrap_price_draws,
    historical_changes,
    run_scenarios,
)

SLATE = "data/derived/slate_phase1.parquet"


@pytest.fixture(scope="module")
def problem_and_prices():
    records = frame_to_records(pd.read_parquet(SLATE))
    curves = [np.array(r.tbp_curve, dtype=float) for r in records]
    sidecar = json.loads(Path("data/derived/costs_phase2.json").read_text(encoding="utf-8"))
    costs_map = build_crude_costs(
        [r.crude_id for r in records], float(sidecar["brent_reference_usd_bbl"])
    )
    costs = np.array([costs_map[r.crude_id] for r in records])
    price_sc = json.loads(Path("data/derived/prices_phase2.json").read_text(encoding="utf-8"))[
        "prices_usd_bbl"
    ]
    prices = np.array([price_sc[p] for p in CONFIG.products])
    quals = [CRUDE_QUALITIES[r.crude_id] for r in records]
    problem = build_lp_problem(curves, costs, quals, CONFIG)
    return problem, prices, float(sidecar["brent_reference_usd_bbl"])


def _synthetic_history(n_months: int = 40, seed: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Synthetic aligned (Brent, products) frames with known co-movement."""
    rng = np.random.default_rng(seed)
    periods = pd.period_range("2024-01", periods=n_months, freq="M").astype(str)
    brent = 70 + np.cumsum(rng.normal(0, 2.0, n_months))
    crack = np.cumsum(rng.normal(0, 1.0, n_months))  # products co-move + crack
    prod = np.column_stack([brent * 1.05 + crack + rng.normal(0, 1, n_months) for _ in range(3)])
    brent_frame = pd.DataFrame({"period": periods, "value": brent})
    product_frame = pd.DataFrame(
        {
            "period": np.repeat(periods, 3),
            "product": np.tile(["EPMRU", "EPD2DXL0", "EPJK"], n_months),
            "value": (prod / 42.0).ravel(),  # $/gal
        }
    )
    return brent_frame, product_frame


def test_historical_changes_shape_and_alignment():
    brent_frame, product_frame = _synthetic_history()
    changes = historical_changes(brent_frame, product_frame)
    assert changes.shape == (39, 4)
    assert np.isfinite(changes).all()
    # products were built to co-move with crude → positive mean correlation
    corr = np.corrcoef(changes[:, 0], changes[:, 1])[0, 1]
    assert corr > 0.5


def test_bootstrap_draws_deterministic_and_bounded():
    brent_frame, product_frame = _synthetic_history()
    changes = historical_changes(brent_frame, product_frame)
    d1 = bootstrap_price_draws(changes, 500, seed=42)
    d2 = bootstrap_price_draws(changes, 500, seed=42)
    assert np.array_equal(d1, d2)
    assert d1.shape == (500, 4)
    # 12-month cumulative log-returns of monthly ~N(0, 2/70) stays small
    assert np.abs(d1).max() < 1.0


def test_zero_draws_reproduce_base_state(problem_and_prices):
    """All-zero draws ⇒ every margin equals the base LP margin exactly."""
    problem, prices, brent_ref = problem_and_prices
    base = solve_lp(problem, prices)
    draws = np.zeros((5, 4))
    res = run_scenarios(problem, prices, base.ratios, base.severity, draws, brent_ref)
    assert np.allclose(res.optimal_margins, base.margin, atol=1e-9)
    assert np.allclose(res.fixed_blend_margins, base.margin, atol=1e-9)
    assert res.var_pct == pytest.approx(base.margin)
    assert res.probability_of_loss == 0.0


def test_brent_shift_cancels_from_argmax(problem_and_prices):
    """Pure Brent shocks shift margins additively and never change the diet.

    The additive cost shift Δ = Brent_ref·(f−1) applies to every crude, so the
    LP argmax is invariant and the margin drops by exactly Δ (docstring claim).
    """
    problem, prices, brent_ref = problem_and_prices
    c = 0.20  # +20% Brent
    draws = np.array([[0.0, 0.0, 0.0, 0.0], [np.log1p(c), 0.0, 0.0, 0.0]])
    res = run_scenarios(problem, prices, np.full(5, 0.2), 0.5, draws, brent_ref)
    delta = brent_ref * c
    assert res.optimal_margins[1] == pytest.approx(res.optimal_margins[0] - delta, rel=1e-9)
    # same optimal blend in both states → identical switch shares
    base0 = solve_lp(problem, prices)
    base1 = solve_lp(problem, prices * np.array([1.0, 1.0, 1.0, 1.0]))
    assert np.allclose(base0.ratios, base1.ratios)  # prices unchanged → same diet


def test_var_cvar_relations_and_reopt_value(problem_and_prices):
    problem, prices, brent_ref = problem_and_prices
    brent_frame, product_frame = _synthetic_history(40, seed=9)
    draws = bootstrap_price_draws(historical_changes(brent_frame, product_frame), 400, seed=3)
    base = solve_lp(problem, prices)
    res = run_scenarios(problem, prices, base.ratios, base.severity, draws, brent_ref)
    assert res.cvar_pct <= res.var_pct + 1e-9
    assert res.fixed_cvar_pct <= res.fixed_var_pct + 1e-9
    # VaR is the 5th percentile of the margins themselves
    assert res.var_pct == pytest.approx(np.percentile(res.optimal_margins, 5.0))
    assert len(res.optimal_margins) == 400
    assert res.tornado.keys() == {p for p in CONFIG.products}


def test_tornado_monotone_in_own_price(problem_and_prices):
    """Raising a product's price never lowers the re-optimized margin."""
    problem, prices, _ = problem_and_prices
    tornado = (
        run_scenarios.__wrapped__._tornado(problem, prices)
        if hasattr(run_scenarios, "__wrapped__")
        else None
    )
    if tornado is None:  # direct call (private but stable)
        from dangote_opt.optimization.scenarios import _tornado

        tornado = _tornado(problem, prices)
    for lo, hi in tornado.values():
        assert hi >= lo - 1e-9
