"""Phase 5 scenario analysis — Monte Carlo over correlated price scenarios.

Design (brief §6 Phase 5: "price shocks, FX depreciation, demand shifts";
open questions answered with data, not assumptions):

* **Shock distribution → historical block bootstrap.** The joint empirical
  distribution of monthly Δlog prices for (crude, gasoline, diesel, jet) is
  sampled from the cached EIA series (2015–2025). Sampling blocks of 12
  consecutive months preserves seasonality/autocorrelation *and* the
  correlation structure of refining margins — crack spreads co-move with
  crude — which independent per-product shocks would destroy. The brief's
  "correlated shocks?" open question is thus answered empirically.
* **10,000 iterations, re-optimization per draw.** Each draw re-solves the
  exact LP (Phase 4 skeleton: constraints fixed, objective = price vector) —
  the planner's optimal response to each market state. The *base* blend
  re-priced under the same draws provides the fixed-blend comparison (the
  value of re-optimization).
* **Cost linkage is exact and simplifies cleanly.** Delivered cost =
  Brent + differential (additive, data/costs.py). A Brent draw shifts every
  crude's cost by the *common additive* amount Δ = Brent_ref·(f − 1), which
  cancels from the LP argmax (Σx = 1) — so the per-draw optimal blend comes
  from the LP at draw prices with base costs, and the true margin subtracts
  Δ. Differentials are preserved by construction.
* **FX & demand shifts (documented scope).** The model is USD-denominated
  single-period and price-taking: crude and products co-move in USD, no
  naira-costed inputs are modeled (spec §7 non-goals), and demand shifts have
  no price-feedback channel. Deterministic factor shifts (e.g. a diesel-demand
  shock as a diesel-price multiplier) are exposed via ``price_multipliers``.

Outputs: per-draw re-optimized margins, fixed-blend margins, VaR/CVaR at the
5th percentile, blend switch frequencies, and a tornado decomposition
(one-at-a-time ±10% product-price shocks on the base LP).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from dangote_opt.config import CONFIG
from dangote_opt.optimization.baselines import LPProblem, solve_lp

FloatArray = NDArray[np.float64]

N_ITERATIONS = 10_000  # brief §6 Phase 5 target
VAR_PERCENTILE = 5.0  # 5% profit VaR/CVaR (market-risk convention)


@dataclass(frozen=True)
class ScenarioResult:
    """Monte Carlo outcome — margins, risk metrics, and response structure."""

    n_iterations: int
    base_margin: float  # LP at base prices (deterministic anchor)
    optimal_margins: FloatArray  # per-draw re-optimized margins, $/bbl
    fixed_blend_margins: FloatArray  # base blend re-priced (no re-opt), $/bbl
    var_pct: float  # 5th percentile, re-optimized margins
    cvar_pct: float  # mean margin conditional on ≤ VaR, re-optimized
    fixed_var_pct: float
    fixed_cvar_pct: float
    probability_of_loss: float  # P(re-optimized margin < 0)
    switch_share: FloatArray  # share of draws each crude is in the optimal diet
    avg_severity: float
    tornado: dict[str, tuple[float, float]]  # product → (margin at −10%, +10%)
    provenance: dict[str, str]


def historical_changes(
    brent_frame: pd.DataFrame,
    product_frame: pd.DataFrame,
    window_months: int | None = None,
) -> FloatArray:
    """Aligned monthly Δlog prices: (Brent, gasoline, diesel, jet), shape (T, 4).

    Args:
        brent_frame: tidy EIA frame (period, value in $/bbl) from the
            ``brent_spot`` cache.
        product_frame: tidy EIA frame (period, product, value in $/gal) from
            the ``us_product_prices`` cache.
        window_months: trailing window; None = the full cached history
            (default — the bootstrap needs as much shock history as possible,
            unlike the level anchors which use trailing 12).

    Returns:
        (T−1, 4) monthly log-changes, aligned on the common months.
    """
    brent_df = brent_frame.sort_values("period")
    if window_months is not None:
        brent_df = brent_df.tail(window_months)
    brent = brent_df["value"].to_numpy(dtype=float)
    prod_df = product_frame.sort_values("period").pivot_table(
        index="period", columns="product", values="value", aggfunc="mean"
    )
    if window_months is not None:
        prod_df = prod_df.tail(window_months)
    prod = prod_df
    products = prod[["EPMRU", "EPD2DXL0", "EPJK"]].to_numpy(dtype=float) * 42.0  # → $/bbl
    n = min(len(brent), len(products))
    levels = np.column_stack([brent[-n:], products[-n:]])
    return np.diff(np.log(levels), axis=0)


def bootstrap_price_draws(changes: FloatArray, n_draws: int, seed: int) -> FloatArray:
    """Draw 12-month cumulative log-return scenarios, shape (n_draws, 4).

    Block bootstrap: each draw sums 12 *consecutive* historical months, so
    within-year co-movement (seasonality + autocorrelation) survives.
    """
    rng = np.random.default_rng(seed)
    t = len(changes)
    if t < 12:
        raise ValueError(f"need ≥12 monthly changes for block bootstrap, got {t}")
    starts = rng.integers(0, t - 12 + 1, size=n_draws)
    idx = starts[:, None] + np.arange(12)[None, :]
    return changes[idx].sum(axis=1)


def run_scenarios(
    problem: LPProblem,
    base_prices: FloatArray,
    base_blend: FloatArray,
    base_severity: float,
    draws: FloatArray,
    brent_ref: float,
    price_multipliers: dict[str, float] | None = None,
    var_percentile: float = VAR_PERCENTILE,
) -> ScenarioResult:
    """Run the Monte Carlo: per-draw re-optimization + risk metrics.

    Args:
        problem: LP skeleton (Phase 4 — constraints are price-independent).
        base_prices: base-state product prices in CONFIG order, $/bbl.
        base_blend: base-state optimal blend ratios (from the base LP).
        base_severity: base-state optimal severity.
        draws: (n_draws, 4) cumulative log-returns — (Brent, gasoline, diesel, jet).
        brent_ref: the base Brent anchor ($/bbl) — converts the Brent factor
            into the common additive cost shift.
        price_multipliers: optional deterministic per-product multipliers
            applied on top of every draw (demand-shift proxy).
        var_percentile: profit VaR/CVaR percentile (default 5%).

    Returns:
        ScenarioResult (see class docstring).
    """
    prices = np.asarray(base_prices, dtype=float)
    base_blend = np.asarray(base_blend, dtype=float)
    n = problem.config.n_crudes
    brent_factor = np.exp(draws[:, 0])  # multiplicative Brent level per draw
    product_factor = np.exp(draws[:, 1:])  # (n_draws, 3): gas/diesel/jet

    if price_multipliers:
        mult = np.array([price_multipliers.get(p, 1.0) for p in CONFIG.products])
        product_factor = product_factor * mult[1:]

    # Base anchor: LP margin at base prices, base costs.
    base_margin = solve_lp(problem, prices).margin

    # Base-blend yields at the base severity (fixed-blend comparison).
    y_fixed = base_blend @ problem.per_crude_yields_s0 + base_severity * (
        base_blend @ problem.per_crude_yield_slopes
    )

    n_draws = len(draws)
    opt_margins = np.empty(n_draws)
    fixed_margins = np.empty(n_draws)
    in_diet = np.zeros(n)
    severities = np.empty(n_draws)

    for i in range(n_draws):
        p = prices.copy()
        p[:3] *= product_factor[i]  # gasoline, diesel, jet; petrochem constant
        # Planner's response: LP at draw prices. The common additive Brent
        # cost shift cancels from the argmax (Σx = 1); subtract it from the
        # margin afterwards (differentials preserved — see module docstring).
        res = solve_lp(problem, p)
        opt_margins[i] = res.margin - brent_ref * (brent_factor[i] - 1.0)
        severities[i] = res.severity
        in_diet += np.asarray(res.ratios) > 1e-3

        # Fixed base blend under the same draw (no re-optimization).
        costs_i = problem.crude_costs + brent_ref * (brent_factor[i] - 1.0)
        fixed_margins[i] = float(y_fixed @ p - base_blend @ costs_i)

    var_level = float(np.percentile(opt_margins, var_percentile))
    tail = opt_margins[opt_margins <= var_level]
    fixed_var = float(np.percentile(fixed_margins, var_percentile))
    fixed_tail = fixed_margins[fixed_margins <= fixed_var]

    return ScenarioResult(
        n_iterations=n_draws,
        base_margin=base_margin,
        optimal_margins=opt_margins,
        fixed_blend_margins=fixed_margins,
        var_pct=var_level,
        cvar_pct=float(tail.mean()) if len(tail) else var_level,
        fixed_var_pct=fixed_var,
        fixed_cvar_pct=float(fixed_tail.mean()) if len(fixed_tail) else fixed_var,
        probability_of_loss=float((opt_margins < 0).mean()),
        switch_share=in_diet / n_draws,
        avg_severity=float(severities.mean()),
        tornado=_tornado(problem, prices),
        provenance={
            "shock_source": "EIA monthly dlog, block-of-12 bootstrap (2015-2025)",
            "cost_linkage": (
                "Brent draw shifts all crude costs additively by "
                "Brent_ref*(f-1); differentials preserved; argmax unchanged"
            ),
            "petrochem": "disclosed placeholder, constant across scenarios",
            "fx_demand_scope": "USD single-period price-taker; no FX/demand channel (spec 7)",
        },
    )


def _tornado(
    problem: LPProblem, base_prices: FloatArray, delta: float = 0.10
) -> dict[str, tuple[float, float]]:
    """One-at-a-time ±delta price shocks on the base LP (tornado decomposition).

    Crude costs held at base — the tornado isolates *product-price* sensitivity
    of the optimally-run refinery (cost-side sensitivity is −1 per $/bbl Brent
    by construction and reported in the summary instead).
    """
    out: dict[str, tuple[float, float]] = {}
    for i, name in enumerate(CONFIG.products):
        lo = base_prices.copy()
        hi = base_prices.copy()
        lo[i] *= 1.0 - delta
        hi[i] *= 1.0 + delta
        out[name] = (solve_lp(problem, lo).margin, solve_lp(problem, hi).margin)
    return out
