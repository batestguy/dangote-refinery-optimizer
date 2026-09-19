"""Baseline contract (spec §3.4, locked) — equal-weight · random search · LP.

The DE result is **always** reported alongside these three baselines, computed
on identical prices, costs, and constraints:

1. **Equal-weight** blend (1/n on each crude) at the default severity — the
   planner's no-optimization case.
2. **Random search** — 10,000 feasible draws (Dirichlet ratios × uniform
   severity); the best feasible margin. "Feasible" is enforced by masking
   infeasible draws out, not by penalizing.
3. **LP optimum** — an *exact* linear program over the same physics, not an
   approximation. The bridge mass balance is affine in severity
   (``yield(x, s) = x·A + s·x·B`` with A, B per-crude constants), so the
   substitution ``u_j = s·x_j`` linearizes it exactly:

       maximize   Σ_p price_p [ Σ_j A_pj x_j + Σ_j B_pj u_j ] − Σ_j cost_j x_j
       s.t.       Σ_j x_j = 1,   0 ≤ u_j ≤ x_j   (⇒ s = Σ u_j ∈ [0, 1])

   The quality specs enter as hard linear constraints via the same affine
   decomposition (RON and RVP-index are ratios of linear aggregations —
   cross-multiplied; cetane and freeze linear). If DE > LP the margin came
   from surrogate nonlinearity beyond the bridge's own physics — reported
   honestly per problem statement §4.

If DE ≤ LP, that is the honest bar from problem statement §4 and is expected
to be near-zero here (the surrogate learns the same linear physics).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linprog

from dangote_opt.config import CONFIG, ProjectConfig
from dangote_opt.features.bridge import (
    blend_yields_batch,
    light_naphtha_fractions,
    tbp_cut_fractions,
)
from dangote_opt.features.quality import RVP_EXPONENT, BatchQualityModel, CrudeQuality
from dangote_opt.optimization.objective import RefineryObjective, simplex_repair

FloatArray = NDArray[np.float64]

# Default severity for the equal-weight baseline (spec §3.4 "default severity";
# the app exposes it as a slider). Mid-range = a moderate operating point.
DEFAULT_SEVERITY = 0.5

RANDOM_SEARCH_DRAWS = 10_000  # spec §3.4: "10k feasible draws"


@dataclass(frozen=True)
class BaselineResult:
    """One baseline's outcome — same units as the DE result ($/bbl margin)."""

    name: str
    ratios: FloatArray
    severity: float
    margin: float


def equal_weight_baseline(
    objective: RefineryObjective, severity: float = DEFAULT_SEVERITY
) -> BaselineResult:
    """Equal-weight blend (1/n each) at the default severity."""
    x = np.full(objective.config.n_crudes, 1.0 / objective.config.n_crudes)
    return BaselineResult("equal_weight", x, severity, objective.margin(x, severity))


def _feasible_mask(objective: RefineryObjective, X: FloatArray, s: FloatArray) -> FloatArray:
    """Boolean feasibility mask over a population (batch when possible)."""
    api = X @ objective.crude_apis
    sulfur = X @ objective.crude_sulfurs
    api_lo, api_hi = objective.config.api_blend_range
    ok = (api >= api_lo) & (api <= api_hi) & (sulfur <= objective.config.sulfur_blend_pct_max)
    if objective.quality_model is not None:
        if objective.batch_quality is not None:
            q = objective.batch_quality.qualities(X, s)
            ok &= q["gasoline_ron"] >= objective.config.gasoline_ron_min
            ok &= q["gasoline_rvp_kpa"] <= objective.config.gasoline_rvp_kpa_max
            ok &= q["jet_freeze_c"] <= objective.config.jet_freeze_point_c_max
            ok &= q["diesel_cetane_idx"] >= objective.config.diesel_cetane_min
        else:
            for i in range(len(X)):
                if ok[i] and objective.constraints_violated(X[i], float(s[i])):
                    ok[i] = False
    return ok


def random_search_baseline(
    objective: RefineryObjective,
    n_draws: int = RANDOM_SEARCH_DRAWS,
    seed: int = CONFIG.de_seed_baseline,
    batch_size: int = 2_000,
) -> BaselineResult:
    """Best margin over ``n_draws`` *feasible* random blends (spec §3.4).

    Dirichlet(α=0.55) ratios (same corner-seeking design as the surrogate
    dataset) × U(0,1) severity; infeasible draws are masked out. Batched via
    ``batch_yields`` when available.
    """
    rng = np.random.default_rng(seed)
    n = objective.config.n_crudes
    best_margin, best_x, best_s = -np.inf, None, None
    remaining = n_draws
    while remaining > 0:
        b = min(batch_size, remaining)
        remaining -= b
        X = rng.dirichlet(np.full(n, 0.55), size=b)
        s = rng.uniform(0.0, 1.0, size=b)
        ok = _feasible_mask(objective, X, s)
        if not ok.any():
            continue
        Xf, sf = X[ok], s[ok]
        if objective.batch_yields is not None:
            Y = np.asarray(objective.batch_yields(Xf, sf), dtype=float)
            margins = Y @ objective.product_prices - Xf @ objective.crude_costs
        else:
            margins = np.array(
                [objective.margin(row, float(si)) for row, si in zip(Xf, sf, strict=True)]
            )
        k = int(np.argmax(margins))
        if margins[k] > best_margin:
            best_margin, best_x, best_s = float(margins[k]), Xf[k], float(sf[k])
    if best_x is None:
        raise RuntimeError(
            "random search found no feasible blend in "
            f"{n_draws} draws — check the constraint bundle"
        )
    return BaselineResult("random_search", best_x, best_s, best_margin)


def lp_baseline(
    curves: list[FloatArray],
    crude_costs: FloatArray,
    product_prices: FloatArray,
    qualities: list[CrudeQuality],
    config: ProjectConfig = CONFIG,
) -> BaselineResult:
    """Exact LP optimum over the bridge's affine-in-severity physics.

    Variables: ``z = [x (n), u (n)]`` with ``u_j = s·x_j`` (see module
    docstring). Quality specs are hard linear constraints built from the same
    ``BatchQualityModel`` coefficients the DE penalty uses — one source of
    truth, no drift between the soft (DE) and hard (LP) formulations.

    Raises:
        RuntimeError: if the LP solver fails or reports infeasibility.
    """
    n = config.n_crudes
    curves = [np.asarray(c, dtype=float) for c in curves]
    cuts = np.array([tbp_cut_fractions(c) for c in curves])  # (n, 5)
    light = light_naphtha_fractions(curves)
    bq = BatchQualityModel.from_slate(curves, qualities)

    # Affine per-crude yields: A = yields at s=0, B = slope per unit s.
    yields0 = blend_yields_batch(
        np.zeros(n),
        np.zeros(n),
        per_crude_cuts=cuts,
        light_naphtha=light,
        ratios_batch=np.eye(n),
        severities=np.zeros(n),
    )
    yields1 = blend_yields_batch(
        np.zeros(n),
        np.zeros(n),
        per_crude_cuts=cuts,
        light_naphtha=light,
        ratios_batch=np.eye(n),
        severities=np.ones(n),
    )
    A, B = yields0, yields1 - yields0  # (n_crudes, 4)

    # Objective: minimize −margin. z = [x, u]
    c = np.concatenate([-(A @ product_prices) + crude_costs, -(B @ product_prices)])

    # u_j − x_j ≤ 0
    rows: list[tuple[FloatArray, float]] = [
        (np.concatenate([np.full(n, -1.0), np.eye(n)[j]]), 0.0) for j in range(n)
    ]

    # --- quality constraints (hard), from BatchQualityModel coefficients ----
    # Gasoline pool volumes: iso + refr (severity-free) + fcc_gas + alk (affine)
    vol_x = bq.iso_a + bq.refr_a + bq.fcc_gas_a + bq.alk_a
    vol_u = bq.fcc_gas_b + bq.alk_b
    # RON: Σ num ≥ 91 · volume  ⇔  91·vol − num ≤ 0
    ron_num_x = (
        bq.iso_ron_num + bq.ron_ref * bq.refr_a + bq.ron_fcc * bq.fcc_gas_a + bq.ron_alk * bq.alk_a
    )
    ron_num_u = bq.ron_fcc * bq.fcc_gas_b + bq.ron_alk * bq.alk_b
    rows.append(
        (
            np.concatenate(
                [
                    config.gasoline_ron_min * vol_x - ron_num_x,
                    config.gasoline_ron_min * vol_u - ron_num_u,
                ]
            ),
            0.0,
        )
    )

    # RVP index: idx_num ≤ 60^1.25 · volume
    idx_x = (
        bq.idx_isom * bq.iso_a
        + bq.idx_ref * bq.refr_a
        + bq.idx_fcc * bq.fcc_gas_a
        + bq.idx_alk * bq.alk_a
    )
    idx_u = bq.idx_fcc * bq.fcc_gas_b + bq.idx_alk * bq.alk_b
    rvp_max_idx = config.gasoline_rvp_kpa_max**RVP_EXPONENT
    rows.append(
        (
            np.concatenate([idx_x - rvp_max_idx * vol_x, idx_u - rvp_max_idx * vol_u]),
            0.0,
        )
    )

    # Jet freeze: Σ x_j·kero_j·(freeze_j − max) ≤ 0 (single-component pool)
    rows.append(
        (
            np.concatenate([bq.kero_a * (bq.freeze - config.jet_freeze_point_c_max), np.zeros(n)]),
            0.0,
        )
    )

    # Diesel cetane: Σ [dist·(cet−45)] + lco·(22−45) ≤ 0 (volume-weighted)
    cet_x = bq.dist_a * (bq.cetane - config.diesel_cetane_min) + bq.lco_a * (
        bq.cetane_lco - config.diesel_cetane_min
    )
    cet_u = bq.lco_b * (bq.cetane_lco - config.diesel_cetane_min)
    rows.append((np.concatenate([cet_x, cet_u]), 0.0))

    A_ub = np.array([r for r, _ in rows])
    b_ub = np.array([b for _, b in rows])

    res = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=np.concatenate([np.ones(n), np.zeros(n)]).reshape(1, -1),
        b_eq=np.array([1.0]),
        bounds=[(0.0, 1.0)] * (2 * n),
        method="highs",
    )
    if not res.success:
        raise RuntimeError(f"LP baseline failed: {res.message}")
    z = res.x
    x = simplex_repair(z[:n])
    severity = float(np.clip(z[n:].sum(), 0.0, 1.0))
    yields = blend_yields_batch(
        np.zeros(n),
        np.zeros(n),
        per_crude_cuts=cuts,
        light_naphtha=light,
        ratios_batch=x.reshape(1, -1),
        severities=np.array([severity]),
    )[0]
    margin = float(yields @ product_prices - x @ crude_costs)
    return BaselineResult("lp", x, severity, margin)
