"""Optimization layer: objective + Phase 4 DE driver and baseline contract."""

from dangote_opt.optimization.baselines import (
    BaselineResult,
    equal_weight_baseline,
    lp_baseline,
    random_search_baseline,
)
from dangote_opt.optimization.de_driver import BlendOptimizationResult, optimize_blend
from dangote_opt.optimization.objective import RefineryObjective, simplex_repair

__all__ = [
    "BaselineResult",
    "BlendOptimizationResult",
    "RefineryObjective",
    "equal_weight_baseline",
    "lp_baseline",
    "optimize_blend",
    "random_search_baseline",
    "simplex_repair",
]
