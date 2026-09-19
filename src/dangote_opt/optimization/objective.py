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
Quality-spec LBIs (RON, cetane, freeze, RVP) join the penalty block via an
injectable ``quality_model`` (features/quality.py computes pool qualities from
the bridge's component streams; spec §4 decision 14, implemented Phase 2).

Baseline contract (spec §3.4, locked): the DE result is always reported
alongside equal-weight, random-search, and LP optima on the same price vector.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from dangote_opt.config import CONFIG, ProjectConfig
from dangote_opt.features.blend import blend_api, blend_sulfur
from dangote_opt.features.quality import quality_violation_magnitude, quality_violations

FloatArray = NDArray[np.float64]

# Yield-model strategy: (blend_ratios, severity) -> 4 yields. The Phase 3 ETR
# surrogate plugs in behind this exact signature (spec §3.6).
YieldModel = Callable[[FloatArray, float], FloatArray]

# Quality-model strategy: (blend_ratios, severity) -> pool-quality dict
# (gasoline_ron, gasoline_rvp_kpa, jet_freeze_c, diesel_cetane_idx). The app
# injects a closure over the slate's curves + component qualities.
QualityModel = Callable[[FloatArray, float], dict[str, float]]

# Batch yield-model strategy: (B, n_crudes) ratios × (B,) severities → (B, 4)
# yields in one vectorized pass. The bridge's exact-linear path and the ETR's
# batch predict both satisfy this — it is what makes vectorized DE fast enough
# for the 30–60 s app budget (spec §3.7).
BatchYieldModel = Callable[[FloatArray, FloatArray], FloatArray]


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
    yield_model: YieldModel | None = field(default=None)
    quality_model: QualityModel | None = field(default=None)
    batch_yields: BatchYieldModel | None = field(default=None)
    batch_quality: object | None = field(default=None)  # features.quality.BatchQualityModel

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

    # -- yield model (Phase 3: ETR surrogate behind the same signature) --------
    def predict_yields(self, ratios: FloatArray, severity: float) -> FloatArray:
        """Yields for (gasoline, diesel, jet, petrochem), fractions of feed.

        With ``yield_model`` set (e.g. the Stage-1 TBP bridge or, later, the ETR
        surrogate), evaluation is delegated to it. Otherwise a documented
        blend-aware placeholder runs: lighter blend (higher API) → more light
        products; sulfur → small distillate loss; severity → VGO→gasoline.
        Placeholder magnitudes are illustrative only.
        """
        if self.yield_model is not None:
            return np.clip(np.asarray(self.yield_model(ratios, severity), dtype=float), 0.0, None)
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
        if self.quality_model is not None:
            violated.extend(quality_violations(self.quality_model(ratios, severity)))
        return violated

    # -- objective -------------------------------------------------------------
    def margin(self, ratios: FloatArray, severity: float) -> float:
        """Unpenalized margin per barrel for an already-feasible (x, s)."""
        yields = self.predict_yields(ratios, severity)
        revenue = float(np.dot(yields, self.product_prices))
        cost = float(np.dot(ratios, self.crude_costs))
        return revenue - cost

    def batch_values(self, pop: FloatArray) -> FloatArray:
        """Vectorized ``__call__`` over a DE population, shape (B, 6) → (B,).

        Same mathematics, one pass: negative margins from a batched yield
        model (``batch_yields`` — the bridge's exact-linear path or the ETR's
        batch predict) plus the identical linear+quadratic penalty from
        blend API/sulfur. When no batch model is supplied the scalar path
        loops (used in tests and with exotic models).

        Note: the quality penalty is NOT re-evaluated here (it matches the
        scalar path only when the quality model is bridge-exact, which the
        app guarantees); with a quality model set and no batch model, callers
        should prefer ``__call__`` for exactness.
        """
        pop = np.asarray(pop, dtype=float)
        X = pop[:, : self.config.n_crudes]
        s = np.clip(pop[:, -1], *self.config.severity_bounds)
        X = np.array([simplex_repair(row) for row in X])  # (B, n) repair
        if self.batch_yields is not None:
            Y = np.asarray(self.batch_yields(X, s), dtype=float)
        else:
            Y = np.array([self.predict_yields(row, si) for row, si in zip(X, s, strict=True)])
        margins = Y @ self.product_prices - X @ self.crude_costs
        api = X @ self.crude_apis
        sulfur = X @ self.crude_sulfurs
        api_lo, api_hi = self.config.api_blend_range
        v_api = np.maximum(api_lo - api, 0.0) + np.maximum(api - api_hi, 0.0)
        v_s = np.maximum(sulfur - self.config.sulfur_blend_pct_max, 0.0)
        penalty = (v_api + v_api**2) + (v_s + v_s**2)
        return -margins + self.config.constraint_penalty * penalty

    def __call__(self, decision_vars: FloatArray) -> float:
        """Return *negative* margin per barrel plus constraint penalty (DE minimizes)."""
        x = simplex_repair(decision_vars[: self.config.n_crudes])
        severity = float(np.clip(decision_vars[-1], *self.config.severity_bounds))
        penalty = self.config.constraint_penalty * self.violation_magnitude(x)
        if self.quality_model is not None:
            quals = self.quality_model(x, severity)
            penalty += self.config.constraint_penalty * quality_violation_magnitude(quals)
        return -self.margin(x, severity) + penalty

    def batch_call(self, pop: FloatArray) -> FloatArray:
        """Batched ``__call__`` (vectorized DE; batch_yields or scalar fallback).

        Accepts populations row-wise (B, n_vars) or in scipy's vectorized
        convention (n_vars, B) — columns are members; normalized internally.

        Exactness contract: with ``batch_yields`` (bridge exact-linear path or
        ETR batch predict) and ``batch_quality`` (exact quality mirror) both
        set, the vectorized value equals ``__call__`` row-wise — each
        violation group (API window, sulfur cap, quality bundle) keeps its own
        linear+quadratic term, matching the scalar composition. Falls back to
        the scalar loop when any exact batch piece is missing.
        """
        pop = np.asarray(pop, dtype=float)
        n_vars = self.config.n_crudes + 1
        if pop.ndim == 2 and pop.shape[0] == n_vars and pop.shape[1] != n_vars:
            pop = pop.T  # scipy vectorized passes (n_vars, S)
        scalar_fallback = self.batch_yields is None or (
            self.quality_model is not None and self.batch_quality is None
        )
        if scalar_fallback:
            return np.array([self.__call__(row) for row in pop])
        X = pop[:, : self.config.n_crudes]
        s = np.clip(pop[:, -1], *self.config.severity_bounds)
        Xr = np.array([simplex_repair(row) for row in X])
        Y = np.asarray(self.batch_yields(Xr, s), dtype=float)
        margins = Y @ self.product_prices - Xr @ self.crude_costs
        api = Xr @ self.crude_apis
        sulfur = Xr @ self.crude_sulfurs
        api_lo, api_hi = self.config.api_blend_range
        v_api = np.maximum(api_lo - api, 0.0) + np.maximum(api - api_hi, 0.0)
        v_s = np.maximum(sulfur - self.config.sulfur_blend_pct_max, 0.0)
        total = (v_api + v_api**2) + (v_s + v_s**2)
        if self.quality_model is not None and self.batch_quality is not None:
            # ``violation_magnitude`` already applies the linear+quadratic form
            # to the summed quality violation (identical to the scalar
            # ``quality_violation_magnitude``) — add it once, do not re-square.
            total = total + self.batch_quality.violation_magnitude(Xr, s)
        return -margins + self.config.constraint_penalty * total
