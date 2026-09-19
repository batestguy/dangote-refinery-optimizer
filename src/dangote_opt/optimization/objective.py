"""Refinery margin objective and constraint handling (brief §3.2, spec §3.4).

Margin per blended barrel:
    M(x, s) = Σ_i yield_i(x, s) · price_i  −  Σ_j x_j · cost_j

Constraint handling for DE (brief §6 Phase 4 open question, decided here):
    * Σx = 1            → simplex *repair* (project, don't penalize)
    * API window, S cap → linear + quadratic *penalty* added to the minimized value.
                          The linear term makes even tiny violations cost more than
                          any realistic margin gain; the quadratic term steers DE back
                          from gross violations.
    * severity bounds   → clipped.
Quality-spec LBIs (RON, cetane, RVP, …) join the penalty block in Phase 2/4.

Baseline contract (spec §3.4, locked): the DE result is always reported
alongside equal-weight, random-search, and LP optima on the same price vector.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from dangote_opt.config import CONFIG, ProjectConfig
from dangote_opt.features.blend import blend_api, blend_sulfur

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
        """Placeholder yields for (gasoline, diesel, jet, petrochem), fractions of feed.

        Deliberately simple but *blend-aware*, so the optimizer has a real trade-off
        (cheap sour/heavy crude vs. higher light-product yield) instead of trivially
        buying the cheapest barrel. Directionally consistent with refining basics:
          * lighter blend (higher API) → more naphtha/gasoline & distillate, less residue
          * higher sulfur → small distillate loss to hydrotreating/HDS
          * FCC severity → converts VGO/residue into gasoline at the expense of the rest
        Yields sum to < 1; the remainder is fuel oil / loss (not a priced product).
        Magnitudes are illustrative only. Contract for Phase 3: same signature, ETR behind it.
        """
        api_lo, api_hi = self.config.api_blend_range
        api, sulfur = self.blend_properties(ratios)
        light = float(np.clip((api - api_lo) / (api_hi - api_lo), 0.0, 1.0))  # 0 = heavy, 1 = light

        base = np.array(
            [
                0.25 + 0.10 * light,  # gasoline
                0.30 + 0.02 * light - 0.02 * sulfur,  # diesel
                0.15 + 0.02 * light,  # jet
                0.12 - 0.04 * light,  # petrochem feed
            ]
        )
        uplift = 0.20 * float(severity)  # conversion moves VGO→gasoline
        yields = base + np.array([uplift, -0.5 * uplift, -0.3 * uplift, -0.2 * uplift])
        return np.clip(yields, 0.0, 1.0)

    # -- constraints (brief §3.2) ---------------------------------------------
    def blend_properties(self, ratios: FloatArray) -> tuple[float, float]:
        """(API_blend, S_blend) under linear blending (features/blend.py rules)."""
        return blend_api(ratios, self.crude_apis), blend_sulfur(ratios, self.crude_sulfurs)

    def violation_magnitude(self, ratios: FloatArray) -> float:
        """Penalty magnitude Σ (v + v²) over API-window and sulfur-cap violations v ≥ 0.

        0.0 means feasible. Multiplied by CONFIG.constraint_penalty in __call__.
        """
        api_lo, api_hi = self.config.api_blend_range
        api, s = self.blend_properties(ratios)
        v_api = max(api_lo - api, 0.0) + max(api - api_hi, 0.0)
        v_s = max(s - self.config.sulfur_blend_pct_max, 0.0)
        return (v_api + v_api**2) + (v_s + v_s**2)

    def constraints_violated(self, ratios: FloatArray, severity: float) -> list[str]:
        """Return human-readable list of violated constraints (empty = feasible)."""
        violated: list[str] = []
        api_lo, api_hi = self.config.api_blend_range
        api, s = self.blend_properties(ratios)
        if not (api_lo <= api <= api_hi):
            violated.append(f"API_blend {api:.1f} outside [{api_lo}, {api_hi}]")
        if s > self.config.sulfur_blend_pct_max:
            violated.append(f"S_blend {s:.2f} > {self.config.sulfur_blend_pct_max}")
        if not (self.config.severity_bounds[0] <= severity <= self.config.severity_bounds[1]):
            violated.append(f"severity {severity:.2f} outside bounds")
        return violated

    # -- objective -------------------------------------------------------------
    def margin(self, ratios: FloatArray, severity: float) -> float:
        """Unpenalized margin per barrel for an already-feasible (x, s)."""
        yields = self.predict_yields(ratios, severity)
        revenue = float(np.dot(yields, self.product_prices))
        cost = float(np.dot(ratios, self.crude_costs))
        return revenue - cost

    def __call__(self, decision_vars: FloatArray) -> float:
        """Return *negative* margin per barrel plus constraint penalty (DE minimizes)."""
        x = simplex_repair(decision_vars[: self.config.n_crudes])
        severity = float(np.clip(decision_vars[-1], *self.config.severity_bounds))
        penalty = self.config.constraint_penalty * self.violation_magnitude(x)
        return -self.margin(x, severity) + penalty
