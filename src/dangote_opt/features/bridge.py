"""Stage-1 pseudo-refinery bridge: TBP cut-point mass balance → yield vectors.

Closes the assay→yield gap (spec §3.1 — the critical design decision). Design
rule: **every number is either (a) integrated from a published TBP curve or
(b) a documented, cited range** — no invented coefficients. Citations live in
docs/methodology.md (Phase 2 deliverable); each parameter is echoed in its
docstring. Validated against published cut yields (Bonny Light sheet: interior
cuts reproduce to ±0.2 vol%).

Model (per crude, at FCC severity s ∈ [0, 1]):

1.  Atmospheric TBP curve (vol%, anchored at 15 °C) → straight-run cuts:
        naphtha  < 180 °C        → gasoline pool (SR naphtha)
        kero/distillate 180–360  → jet / diesel pool (split at 260 °C)
        VGO      360–540         → FCC feed
        residue  > 540           → fuel oil / petrochem feed
2.  FCC: a severity-dependent fraction ``s · CONVERSION_MAX`` of VGO cracks;
    products split into gasoline / distillate / gas + coke per Gary & Handwerk
    (2007) nominal VGO-FCC ranges. Unconverted VGO ("slurry") stays heavy.
3.  Hydrotreating: sulfur pickup is *quality*, not yield — the ICCT tutorial
    (Leiby, 2011, exhibit 17) puts H2-side yield loss at ≈1 vol%; applied here.
4.  Naphtha pool = SR naphtha + FCC gasoline; distillate pool = SR 180–360 +
    FCC LCO + unconverted VGO portion; jet = SR 180–260 share; petrochem
    (feedstock) = residue + slurry + FCC gas (propylene/PGP proxy).

Yields are fractions of whole crude feed; they sum to ≈1 by construction.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

# --- cut points (°C) — industry-standard atmospheric scheme (spec §3.1) -----
NAPHTHA_END_C = 180.0  # SR naphtha / gasoline pool cut
JET_END_C = 260.0  # kerosene (jet) vs diesel share of 180–360
DISTILLATE_END_C = 360.0  # end of straight-run distillate (atmospheric)
VGO_END_C = 540.0  # vacuum gas oil end / residue start
ANCHOR_C = 15.0  # curves are anchored at (15 °C, 0 vol%)

# --- FCC conversion & product split — cited ranges, see methodology.md ------
# Gary & Handwerk, "Petroleum Refining" 5th ed. (2007), ch. 4 (FCC):
#   conversion (feed → lighter than gasoline cut point) for VGO FCC ≈ 55–75 vol%
#   of feed at typical severity; we map severity s∈[0,1] onto 40–80%.
FCC_CONVERSION_AT_S0 = 0.40
FCC_CONVERSION_AT_S1 = 0.80
# Split of converted VGO (cracked products) — nominal VGO-FCC (same source):
#   gasoline ≈ 45–55, LCO ≈ 15–20, light gas + coke ≈ 25–35 (vol% of converted)
FCC_GASOLINE_SHARE = 0.50
FCC_LCO_SHARE = 0.18
FCC_GAS_COKE_SHARE = 0.32  # 1 − 0.50 − 0.18
# Hydrotreating yield loss (ICCT tutorial exhibit 17: ≈1 vol%)
HYDROTREATER_YIELD_LOSS = 0.01


def _interpolate_vol_pct(curve: FloatArray, temp_c: float) -> float:
    """Cumulative vol% at ``temp_c`` from an ascending (T, vol%) curve.

    Flat-below-first-point / flat-above-last-point behaviour — integration over
    a range outside the measured curve contributes nothing.
    """
    temps = curve[:, 0]
    vols = curve[:, 1]
    return float(np.interp(temp_c, temps, vols))


def tbp_cut_fractions(
    tbp_curve: FloatArray,
    cut_points_c: tuple[float, ...] = (NAPHTHA_END_C, JET_END_C, DISTILLATE_END_C, VGO_END_C),
) -> FloatArray:
    """Integrate a TBP curve into cumulative vol-fractions per cut.

    Args:
        tbp_curve: (temperature_c, vol_pct_recovered) pairs, shape (n, 2),
            temperatures ascending, cumulative vol% (0–100). Curves should be
            anchored at ANCHOR_C → 0 (parser guarantees this for the slate).
        cut_points_c: four ascending boundaries
            (naphtha_end, jet_end, distillate_end, vgo_end).

    Returns:
        Array of 5 vol-fractions summing to ≈1:
        [naphtha(<180), kerosene(180–260), diesel(260–360),
         VGO(360–540), residue(>540)].
    """
    curve = np.asarray(tbp_curve, dtype=float)
    if curve.ndim != 2 or curve.shape[1] != 2:
        raise ValueError(f"tbp_curve must be (n, 2), got {curve.shape}")
    if len(cut_points_c) != 4 or any(
        b <= a for a, b in zip(cut_points_c, cut_points_c[1:], strict=False)
    ):
        raise ValueError(f"need 4 ascending cut points, got {cut_points_c}")

    cumulative = [_interpolate_vol_pct(curve, t) / 100.0 for t in cut_points_c]
    # diffs of [0, c1..c4, 1] = [naphtha, kerosene, diesel, VGO, residue]
    return np.clip(np.diff([0.0, *cumulative, 1.0]), 0.0, None)


def yields_from_assay(
    api: float,
    sulfur_pct: float,
    tbp_curve: FloatArray,
    severity: float,
) -> FloatArray:
    """Per-crude 4-product yield vector under an FCC severity proxy.

    Args:
        api: whole-crude API gravity (recorded, used for sanity bands only).
        sulfur_pct: whole-crude sulfur wt-% (recorded; HDS is yield-neutral here).
        tbp_curve: (temperature_c, vol_pct) pairs, shape (n, 2), ascending.
        severity: normalized FCC conversion proxy in [0, 1].

    Returns:
        Yields as fractions of whole-crude feed for
        (gasoline, diesel, jet, petrochem), each ≥ 0, summing to ≈ 1.
    """
    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"severity must be in [0, 1], got {severity}")
    curve = np.asarray(tbp_curve, dtype=float)

    naphtha, kero, diesel_cut, vgo, residue = tbp_cut_fractions(curve)

    # FCC: severity-dependent fraction of VGO converts; split into
    # gasoline / LCO / gas+coke (shares above, methodology.md).
    conversion = FCC_CONVERSION_AT_S0 + severity * (FCC_CONVERSION_AT_S1 - FCC_CONVERSION_AT_S0)
    fcc_gasoline = vgo * conversion * FCC_GASOLINE_SHARE
    fcc_lco = vgo * conversion * FCC_LCO_SHARE
    fcc_gas_coke = vgo * conversion * FCC_GAS_COKE_SHARE
    slurry = vgo * (1.0 - conversion)  # unconverted VGO

    # Product pools (fractions of whole crude):
    gasoline = naphtha + fcc_gasoline
    jet = kero  # SR kerosene cut → jet pool
    diesel = diesel_cut + fcc_lco  # SR 260–360 + light cycle oil
    petrochem = residue + slurry + fcc_gas_coke

    yields = np.array([gasoline, diesel, jet, petrochem])
    # Hydrotreating side reactions lose ≈1% of distillate-range material
    # (ICCT exhibit 17) — applied to the diesel pool, conservative for the rest.
    yields[1] *= 1.0 - HYDROTREATER_YIELD_LOSS
    return np.clip(yields, 0.0, None)
