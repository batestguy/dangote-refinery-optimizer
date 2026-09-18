"""Stage-1 pseudo-refinery bridge: TBP cut-point mass balance → yield vectors.

Closes the assay→yield gap (spec §3.1 — the critical design decision):
    TBP curve → cut fractions (naphtha / middle distillate / VGO / residue)
    → published FCC/HDS/reformer yield correlations → per-crude yield vector.
FCCU dataset statistics calibrate the yield-vs-severity *shape* in Stage 2.

Every correlation used must be cited in docs/methodology.md (Phase 2 deliverable).
Implemented in Phase 2.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def tbp_cut_fractions(
    tbp_curve: FloatArray,
    cut_points_c: tuple[float, ...] = (180.0, 360.0, 540.0),
) -> FloatArray:
    """Integrate a TBP curve into mass fractions per cut.

    Args:
        tbp_curve: (temperature_c, mass_pct) pairs, shape (n_points, 2), ascending T.
        cut_points_c: boundaries for naphtha / middle distillate / VGO / residue.

    Returns:
        Array of 4 mass fractions summing to 1.

    Raises:
        NotImplementedError: Phase 2.
    """
    raise NotImplementedError("Phase 2: cut-point integration (see docs/methodology.md)")


def yields_from_assay(
    api: float,
    sulfur_pct: float,
    tbp_curve: FloatArray,
    severity: float,
) -> FloatArray:
    """Per-crude 4-product yield vector under an FCC severity proxy.

    Args:
        api: whole-crude API gravity.
        sulfur_pct: whole-crude sulfur wt-%.
        tbp_curve: (temperature_c, mass_pct) pairs, shape (n_points, 2).
        severity: normalized FCC conversion proxy in [0, 1].

    Returns:
        Yields for (gasoline, diesel, jet, petrochem), each in [0, 1].

    Raises:
        NotImplementedError: Phase 2 (correlation set chosen at Phase 2 kickoff).
    """
    raise NotImplementedError("Phase 2: published FCC/HDS/reformer yield correlations")
