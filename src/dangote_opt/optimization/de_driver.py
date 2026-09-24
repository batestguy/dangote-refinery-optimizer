"""Phase 4: differential evolution driver over blend ratios + FCC severity.

Contract (spec §3.4/§3.6):
- Variables: 5 blend ratios (sum-to-1 via simplex repair) + 1 severity proxy.
- Mandatory baselines reported alongside: equal-weight, random search, LP optimum.
- Sensitivity: ≥100 seeds; convergence plots are a Phase 4 deliverable.

Implementation notes (Phase 4 speed work, spec §3.7 30–60 s budget):
- scipy DE runs with ``vectorized=True`` over ``objective.batch_call`` — the
  whole population is evaluated in one batched pass (bridge exact-linear path
  or ETR batch predict + exact quality mirror), turning the ~20k scalar
  objective calls into a few hundred vectorized ones.
- ``update_interval``/callback capture the best-value-per-iteration history
  for the convergence plot (viz/convergence.py).
- A wall-clock budget guard is recorded in the result dict; the caller (app)
  decides UX. No silent budget overrun: if a run exceeds the budget, the
  result carries ``over_budget=True`` and the recorded runtime.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import OptimizeResult, differential_evolution

from dangote_opt.config import CONFIG, ProjectConfig
from dangote_opt.optimization.baselines import (
    DEFAULT_SEVERITY,
    BaselineResult,
    equal_weight_baseline,
    lp_baseline,
    random_search_baseline,
)
from dangote_opt.optimization.objective import RefineryObjective, simplex_repair

FloatArray = NDArray[np.float64]

# App deep re-opt budget (spec §3.7 / locked decision 15: 30–60 s on free tier)
DE_BUDGET_S = 60.0


@dataclass(frozen=True)
class BlendOptimizationResult:
    """Everything the app and the sensitivity study consume, in one object."""

    best_x: FloatArray
    best_severity: float
    best_margin: float  # unpenalized $/bbl
    feasible: bool
    violations: list[str]
    baselines: dict[str, BaselineResult]
    convergence: FloatArray  # best objective value per DE iteration
    runtime_s: float
    over_budget: bool
    seed: int
    n_evaluations: int
    de_message: str
    de_success: bool
    extras: dict[str, object] = field(default_factory=dict)


def optimize_blend(
    objective: RefineryObjective,
    *,
    seed: int | None = None,
    config: ProjectConfig = CONFIG,
    maxiter: int | None = None,
    popsize: int | None = None,
    tol: float = 1e-3,
    with_baselines: bool = True,
    lp_inputs: tuple[list[FloatArray], FloatArray, FloatArray, list] | None = None,
    progress_callback: Callable[[int, float], None] | None = None,
) -> BlendOptimizationResult:
    """Run vectorized DE + the mandatory 3-way baseline comparison (spec §3.4).

    Args:
        objective: RefineryObjective (batch_yields/batch_quality set → fast path).
        seed: DE seed; defaults to ``config.de_seed_baseline``.
        config: project config (DE budget constants).
        maxiter: override DE generations (sensitivity studies use fewer).
        popsize: override DE population multiplier.
        tol: DE convergence tolerance (relative std of population energies).
        with_baselines: compute the 3-way baseline table (disable inside
            sensitivity studies — the baselines are seed-independent).
        lp_inputs: ``(curves, crude_costs, product_prices, qualities)`` for the
            LP baseline; when None the LP is skipped (recorded as absent).
        progress_callback: optional ``(iteration, best_value)`` sink for UX.

    Returns:
        BlendOptimizationResult with the DE optimum, baselines, convergence
        history, runtime, and budget flag.
    """
    seed = config.de_seed_baseline if seed is None else seed
    maxiter = config.de_maxiter if maxiter is None else maxiter
    popsize = config.de_popsize if popsize is None else popsize
    bounds = [(0.0, 1.0)] * config.n_crudes + [tuple(config.severity_bounds)]

    history: list[float] = []

    def track(intermediate_result: OptimizeResult) -> None:
        # scipy inspects the signature: params == {'intermediate_result'} →
        # modern contract, receives the OptimizeResult each iteration.
        fun = float(intermediate_result.fun)
        history.append(fun)
        if progress_callback is not None:
            progress_callback(len(history), fun)

    t0 = time.perf_counter()
    result = differential_evolution(
        objective.batch_call,
        bounds,
        maxiter=maxiter,
        popsize=popsize,
        seed=seed,
        polish=False,
        tol=tol,
        vectorized=True,
        init="sobol",  # better initial coverage than latinhypercube at small budgets
        updating="deferred",  # required with vectorized=True
        callback=track,
    )
    runtime = time.perf_counter() - t0

    x = simplex_repair(result.x[: config.n_crudes])
    severity = float(np.clip(result.x[-1], *config.severity_bounds))
    margin = objective.margin(x, severity)
    violations = objective.constraints_violated(x, severity)

    baselines: dict[str, BaselineResult] = {}
    if with_baselines:
        baselines["equal_weight"] = equal_weight_baseline(objective, DEFAULT_SEVERITY)
        baselines["random_search"] = random_search_baseline(objective, seed=seed)
        if lp_inputs is not None:
            curves, costs, prices, quals = lp_inputs
            baselines["lp"] = lp_baseline(curves, costs, prices, quals, config)

    return BlendOptimizationResult(
        best_x=x,
        best_severity=severity,
        best_margin=margin,
        feasible=not violations,
        violations=violations,
        baselines=baselines,
        convergence=np.asarray(history, dtype=float),
        runtime_s=runtime,
        over_budget=runtime > DE_BUDGET_S,
        seed=seed,
        n_evaluations=int(result.nfev),
        de_message=str(result.message),
        de_success=bool(result.success),
        extras={"polish": False, "vectorized": True, "init": "sobol", "tol": tol},
    )
