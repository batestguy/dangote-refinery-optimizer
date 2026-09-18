"""Central configuration — single source of numeric truth for locked decisions.

Scope guards (plan-improvement-spec.md §3.3/§3.6):
- 4 products, 5-crude slate, single period.
- Decision variables: blend ratios + one FCC severity proxy (unit-level tuning despecified).
- Quality-spec bundle (RON, diesel sulfur, cetane, freeze point, RVP) enters Phase 2
  as *constraints*, never as extra surrogate outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProjectConfig:
    """Immutable project-wide constants. Change here, not in code."""

    products: tuple[str, ...] = ("gasoline", "diesel", "jet", "petrochem")
    n_crudes: int = 5

    # Decision variables: blend ratios (n_crudes) + FCC severity proxy
    severity_bounds: tuple[float, float] = (0.0, 1.0)  # normalized conversion proxy

    # Quality-spec bundle — Phase 2 constraints (linear blend indices live in features/)
    gasoline_ron_min: float = 91.0
    diesel_sulfur_ppm_max: float = 50.0
    diesel_cetane_min: float = 45.0
    jet_freeze_point_c_max: float = -47.0
    gasoline_rvp_kpa_max: float = 60.0

    # Blend design limits (brief §3.2)
    api_blend_range: tuple[float, float] = (30.0, 45.0)  # Dangote-scale design window
    sulfur_blend_pct_max: float = 1.5

    # DE budget (spec §3.7: deep re-opt, 30–60 s target on free tier)
    de_maxiter: int = 250
    de_popsize: int = 15
    de_seed_baseline: int = 42
    de_seeds_sensitivity: int = 100

    # Pricing fallback (USD/bbl) — placeholder until EIA pulls land in Phase 1
    default_prices: dict[str, float] = field(
        default_factory=lambda: {
            "gasoline": 95.0,
            "diesel": 100.0,
            "jet": 90.0,
            "petrochem": 70.0,
        }
    )


CONFIG = ProjectConfig()
