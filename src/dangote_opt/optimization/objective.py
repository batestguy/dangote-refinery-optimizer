"""Refinery margin objective and constraint checking (brief §3.2, spec §3.4).

Margin per blended barrel:
    M(x) = Σ_i yield_i(x) · price_i  −  Σ_j x_j · cost_j

Baseline contract (spec §3.4, locked): the DE result is always reported
alongside equal-weight, random-search, and LP optima on the same price vector.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from dangote_opt.config import CONFIG, ProjectConfig

FloatArray = NDArray[np.float64]


def simplex_repair(x: FloatArray) -> FloatArray:
    """Project an arbitrary non-negative vector onto the probability simplex.

    Uses the standard clipping-and-renormalize repair (penalty-free constraint
    handling for DE, brief §6 Phase 4 open question — repair chosen over penalty).
    """
    x = np.clip(np.asarray(x, dtype=float), 0.0, None)
    s = x.sum()
    if s <= 0:
        return np.full_like(x, 1.0 / len(x))
    return x / s


@dataclass
class RefineryObjective:
    """Callable margin objective over (blend ratios, severity).

    In Phase 3 the yield model becomes the ETR surrogate; until then a
    crude linear placeholder keeps the optimizer testable end-to-end.
    """

    crude_apis: FloatArray
    crude_sulfurs: FloatArray
    crude_costs: FloatArray
    product_prices: FloatArray
    config: ProjectConfig = CONFIG

    def __post_init__(self) -> None:
        n = self.config.n_crudes
        arrays = (
            ("apis", self.crude_apis),
            ("sulfurs", self.crude_sulfurs),
            ("costs", self.crude_costs),
        )
        for name, arr in arrays:
            if len(arr) != n:
                raise ValueError(f"crude_{name} must have length {n}, got {len(arr)}")
        if len(self.product_prices) != len(self.config.products):
            n_products = len(self.config.products)
            raise ValueError(
                f"product_prices must have length {n_products}, got {len(self.product_prices)}"
            )

    # -- placeholder yield model (replaced by ETR surrogate in Phase 3) --------
    def predict_yields(self, ratios: FloatArray, severity: float) -> FloatArray:
        """Placeholder: severity shifts naphtha→gasoline conversion linearly.

        Contract for Phase 3: same signature, ETR behind it.
        """
        base = np.array([0.30, 0.30, 0.15, 0.10])  # plausible whole-crude cuts
        uplift = 0.20 * float(severity)  # conversion moves VGO→gasoline
        yields = base + np.array([uplift, -0.5 * uplift, -0.3 * uplift, -0.2 * uplift])
        return np.clip(yields, 0.0, None)

    # -- constraints (brief §3.2) ---------------------------------------------
    def constraints_violated(self, ratios: FloatArray, severity: float) -> list[str]:
        """Return human-readable list of violated constraints (empty = feasible)."""
        violated: list[str] = []
        api_lo, api_hi = self.config.api_blend_range
        api = float(np.dot(ratios, self.crude_apis))
        s = float(np.dot(ratios, self.crude_sulfurs))
        if not (api_lo <= api <= api_hi):
            violated.append(f"API_blend {api:.1f} outside [{api_lo}, {api_hi}]")
        if s > self.config.sulfur_blend_pct_max:
            violated.append(f"S_blend {s:.2f} > {self.config.sulfur_blend_pct_max}")
        if not (self.config.severity_bounds[0] <= severity <= self.config.severity_bounds[1]):
            violated.append(f"severity {severity:.2f} outside bounds")
        return violated

    # -- objective -------------------------------------------------------------
    def __call__(self, decision_vars: FloatArray) -> float:
        """Return *negative* margin per barrel (for minimization by DE)."""
        x = simplex_repair(decision_vars[: self.config.n_crudes])
        severity = float(np.clip(decision_vars[-1], *self.config.severity_bounds))
        yields = self.predict_yields(x, severity)
        revenue = float(np.dot(yields, self.product_prices))
        cost = float(np.dot(x, self.crude_costs))
        return -(revenue - cost)
