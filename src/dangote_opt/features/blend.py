"""Linear blending rules for whole-crude properties (brief §3.2).

Valid for API gravity and sulfur wt-% under the locked linear-blending assumption:
    P_blend = Σ_j x_j · P_j
Non-linear blending indices (octane, RVP, cetane) are added in Phase 2 with the
quality-spec constraint bundle (spec §3.3) — they do NOT live here.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def blend_property(ratios: FloatArray, values: FloatArray) -> float:
    """Weighted blend property P_blend = x · P.

    Args:
        ratios: blend ratios, shape (n_crudes,).
        values: per-crude property values, shape (n_crudes,).

    Returns:
        The blended property value.

    Raises:
        ValueError: on shape mismatch or negative ratios.
    """
    ratios = np.asarray(ratios, dtype=float)
    values = np.asarray(values, dtype=float)
    if ratios.shape != values.shape:
        raise ValueError(f"shape mismatch: ratios {ratios.shape} vs values {values.shape}")
    if np.any(ratios < 0):
        raise ValueError("blend ratios must be non-negative")
    return float(np.dot(ratios, values))


def blend_api(ratios: FloatArray, apis: FloatArray) -> float:
    """Blended API gravity (linear, industry-standard approximation)."""
    return blend_property(ratios, apis)


def blend_sulfur(ratios: FloatArray, sulfurs: FloatArray) -> float:
    """Blended sulfur wt-% (linear)."""
    return blend_property(ratios, sulfurs)
