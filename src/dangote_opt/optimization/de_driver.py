"""Phase 4: differential evolution driver over blend ratios + FCC severity.

Contract (spec §3.4/§3.6):
- Variables: 5 blend ratios (sum-to-1 via simplex repair) + 1 severity proxy.
- Mandatory baselines reported alongside: equal-weight, random search, LP optimum.
- Sensitivity: ≥100 seeds; convergence plots are a Phase 4 deliverable.
"""

from __future__ import annotations


def optimize_blend(
    objective,  # noqa: ANN001 - RefineryObjective; typed in Phase 4
    seeds: list[int] | None = None,
):
    """Run scipy.optimize.differential_evolution + baseline comparisons.

    Args:
        objective: RefineryObjective instance.
        seeds: seeds for sensitivity analysis; defaults to [CONFIG.de_seed_baseline].

    Returns:
        Dict with keys: best_x, best_margin, baselines (equal_weight, random, lp),
        per-seed results, convergence history.

    Raises:
        NotImplementedError: Phase 4.
    """
    raise NotImplementedError("Phase 4: DE driver + 3-way baseline comparison (spec §3.4)")
