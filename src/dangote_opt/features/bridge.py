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
4.  Octane units (fixed-fraction transforms — without them no realistic blend
    meets the RON 91 gasoline spec, because SR naphtha blends at RON ≈ 58):
        light naphtha (<80 °C)  → isomerate, yield-neutral (RON uplift constant,
                                  features/quality.py)
        mid naphtha (80–180 °C) → reformate at REFORMER_YIELD (rest → LPG/H2,
                                  routed to the petrochem/feed pool)
        FCC gas + coke          → alkylate at ALKYLATE_SHARE (rest = fuel gas +
                                  coke + propylene → petrochem/feed pool)
5.  Product pools: gasoline = isomerate + reformate + alkylate; jet = SR kero
    (180–260 °C); diesel = SR distillate (260–360 °C) + FCC LCO, less HT loss;
    petrochem/feed = residue + slurry + un-alkylated FCC gas + reformer LPG.

Yields are fractions of whole crude feed; they sum to ≈1 by construction.
``component_volumes()`` exposes the pre-pooling streams so the quality-spec
constraints (features/quality.py) can compute pool qualities from the same
mass balance — one source of truth.
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

# --- octane units — cited ranges, see methodology.md §3b -------------------
# Reformer: mid naphtha → reformate. Reformate yield 80–88 vol% of feed at
# high severity (Gary & Handwerk ch. 9 reformer yield tables); balance is LPG
# + H2 → petrochem/feed pool. Reformate RON set by reformer severity, not by
# the crude — constant in features/quality.py (cited there).
REFORMER_YIELD = 0.85
# Alkylation: the FCC C3/C4 fraction (inside the gas+coke lump) → alkylate at
# ~50% of that lump; the rest is fuel gas + coke + polymer-grade propylene
# (→ petrochem pool). Conservative: alkylate yield on actual C4s is ≈1.0–1.7
# vol (Gary & Handwerk ch. 7), but the gas+coke lump also contains dry gas and
# coke, so 50% of the lump keeps the mass balance honest.
ALKYLATE_SHARE = 0.50
# Light naphtha (<80 °C) → isomerization: yield-neutral (isomerization is a
# rearrangement, ≈100 vol% yield), octane uplift is applied in
# features/quality.py where the RON math lives.
ISOM_YIELD = 1.0

# Butane pull-off: the front end of SR naphtha (C4/C5-rich, highest-RVP
# material) is stripped to LPG for gasoline-pool RVP control — standard
# practice (RVP is managed via butane content). Share of light naphtha,
# ASSUMED (methodology.md §3b); routes that volume to the petrochem/LPG pool.
BUTANE_PULL_SHARE = 0.25

# Light-naphtha boundary inside the SR naphtha cut (<180 °C): the TotalEnergies
# sheets publish quality for 15–80 °C vs 80–175 °C separately, and only the
# light fraction goes to isomerization.
LIGHT_NAPHTHA_END_C = 80.0


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
    light_nap = _interpolate_vol_pct(curve, LIGHT_NAPHTHA_END_C) / 100.0
    mid_nap = naphtha - light_nap

    # FCC: severity-dependent fraction of VGO converts; split into
    # gasoline / LCO / gas+coke (shares above, methodology.md).
    conversion = FCC_CONVERSION_AT_S0 + severity * (FCC_CONVERSION_AT_S1 - FCC_CONVERSION_AT_S0)
    fcc_gasoline = vgo * conversion * FCC_GASOLINE_SHARE
    fcc_lco = vgo * conversion * FCC_LCO_SHARE
    fcc_gas_coke = vgo * conversion * FCC_GAS_COKE_SHARE
    slurry = vgo * (1.0 - conversion)  # unconverted VGO

    # Octane units (fixed fractions — methodology.md §3b)
    butane_lpg = light_nap * BUTANE_PULL_SHARE
    light_nap_net = light_nap * (1.0 - BUTANE_PULL_SHARE)
    reformate = mid_nap * REFORMER_YIELD
    reformer_lpg = mid_nap * (1.0 - REFORMER_YIELD)
    alkylate = fcc_gas_coke * ALKYLATE_SHARE
    fcc_gas_nonalk = fcc_gas_coke * (1.0 - ALKYLATE_SHARE)

    # Product pools (fractions of whole crude):
    gasoline = light_nap_net * ISOM_YIELD + reformate + fcc_gasoline + alkylate
    jet = kero  # SR kerosene cut → jet pool
    diesel = diesel_cut + fcc_lco  # SR 260–360 + light cycle oil
    petrochem = residue + slurry + fcc_gas_nonalk + reformer_lpg + butane_lpg

    yields = np.array([gasoline, diesel, jet, petrochem])
    # Hydrotreating side reactions lose ≈1% of distillate-range material
    # (ICCT exhibit 17) — applied to the diesel pool, conservative for the rest.
    yields[1] *= 1.0 - HYDROTREATER_YIELD_LOSS
    return np.clip(yields, 0.0, None)


def light_naphtha_fractions(
    curves: list[FloatArray] | tuple[FloatArray, ...] | None,
) -> FloatArray:
    """Per-crude light-naphtha fraction (<80 °C) of whole crude, shape (n,).

    Precompute once per slate; ``blend_yields_batch`` consumes the vector so
    the batch path never re-interpolates curves (hot-path hygiene).
    """
    if curves is None:
        raise ValueError("curves required to compute light-naphtha fractions")
    return np.array(
        [
            _interpolate_vol_pct(np.asarray(c, dtype=float), LIGHT_NAPHTHA_END_C) / 100.0
            for c in curves
        ]
    )


def blend_yields_batch(
    apis: FloatArray,
    sulfurs: FloatArray,
    curves: list[FloatArray] | tuple[FloatArray, ...] | None = None,
    per_crude_cuts: FloatArray | None = None,
    light_naphtha: FloatArray | None = None,
    ratios_batch: FloatArray | None = None,
    severities: FloatArray | None = None,
) -> FloatArray:
    """Vectorized blend yields: (B, n_crudes) ratios × (B,) severities → (B, 4).

    The blend mass balance is *exactly linear* in the blend's cut fractions,
    with a single shared nonlinearity: the FCC conversion multiplies the
    blended VGO fraction by a factor that depends only on severity.
    ``blend_yields_batch`` reproduces ``yields_from_assay`` pooled per
    blend exactly (pinned to machine precision by tests), while evaluating
    an entire DE population in one pass — this is what keeps the deep
    re-opt inside the 30–60 s budget (spec §3.7).

    Args:
        apis: whole-crude API gravities, shape (n_crudes,) — carried for
            interface parity (the yield math is curve-driven).
        sulfurs: whole-crude sulfur wt-%, shape (n_crudes,) — recorded only.
        curves: one TBP curve per crude (same order), used when
            ``per_crude_cuts`` is None.
        per_crude_cuts: optional precomputed (n_crudes, 5) cut matrix from
            ``tbp_cut_fractions`` (the hot path; avoids re-interpolating
            every call). When given, also pass ``light_naphtha`` (or ``curves``
            to derive it).
        light_naphtha: optional precomputed per-crude light-naphtha fraction
            (<80 °C of whole crude) from ``light_naphtha_fractions``.
        ratios_batch: blend ratios, shape (B, n_crudes), rows sum ≈ 1.
        severities: FCC severity proxy, shape (B,) or scalar.

    Returns:
        (B, 4) yields in (gasoline, diesel, jet, petrochem) order, fractions
        of whole-crude feed, each ≥ 0, rows summing to ≈ 1.
    """
    if ratios_batch is None:
        raise ValueError("ratios_batch is required")
    X = np.asarray(ratios_batch, dtype=float)
    if X.ndim != 2:
        raise ValueError(f"ratios_batch must be (B, n_crudes), got {X.shape}")
    if severities is None:
        raise ValueError("severities is required")
    s = np.asarray(severities, dtype=float)
    if s.ndim == 0:
        s = np.full(len(X), float(s))
    if len(s) != len(X):
        raise ValueError(f"severities length {len(s)} != ratios_batch rows {len(X)}")
    if not np.all((s >= 0.0) & (s <= 1.0)):
        raise ValueError("severity must be in [0, 1]")

    if per_crude_cuts is None:
        if curves is None:
            raise ValueError("provide curves or per_crude_cuts")
        per_crude_cuts = np.array([tbp_cut_fractions(np.asarray(c, dtype=float)) for c in curves])
        light = light_naphtha_fractions(curves)
    else:
        if light_naphtha is not None:
            light = np.asarray(light_naphtha, dtype=float)
        elif curves is not None:
            light = light_naphtha_fractions(curves)
        else:
            raise ValueError("per_crude_cuts requires light_naphtha or curves")
    C = np.asarray(per_crude_cuts, dtype=float)
    if C.shape != (X.shape[1], 5):
        raise ValueError(f"per_crude_cuts must be (n_crudes, 5), got {C.shape}")
    if light.shape != (X.shape[1],):
        raise ValueError(f"light_naphtha must be (n_crudes,), got {light.shape}")

    cuts = X @ C  # (B, 5): [naphtha, kero, diesel_cut, vgo, residue]
    naphtha, kero, diesel_cut, vgo, residue = (cuts[:, k] for k in range(5))
    light_nap = X @ light
    mid_nap = naphtha - light_nap

    # Same mass balance as yields_from_assay, vectorized over the batch.
    conversion = FCC_CONVERSION_AT_S0 + s * (FCC_CONVERSION_AT_S1 - FCC_CONVERSION_AT_S0)
    fcc_gasoline = vgo * (conversion * FCC_GASOLINE_SHARE)
    fcc_lco = vgo * (conversion * FCC_LCO_SHARE)
    fcc_gas_coke = vgo * (conversion * FCC_GAS_COKE_SHARE)
    slurry = vgo * (1.0 - conversion)

    butane_lpg = light_nap * BUTANE_PULL_SHARE
    light_nap_net = light_nap * (1.0 - BUTANE_PULL_SHARE)
    reformate = mid_nap * REFORMER_YIELD
    reformer_lpg = mid_nap * (1.0 - REFORMER_YIELD)
    alkylate = fcc_gas_coke * ALKYLATE_SHARE
    fcc_gas_nonalk = fcc_gas_coke * (1.0 - ALKYLATE_SHARE)

    gasoline = light_nap_net * ISOM_YIELD + reformate + fcc_gasoline + alkylate
    jet = kero
    diesel = diesel_cut + fcc_lco
    petrochem = residue + slurry + fcc_gas_nonalk + reformer_lpg + butane_lpg

    yields = np.column_stack([gasoline, diesel, jet, petrochem])
    yields[:, 1] *= 1.0 - HYDROTREATER_YIELD_LOSS
    return np.clip(yields, 0.0, None)


def component_volumes(
    tbp_curve: FloatArray,
    severity: float,
) -> dict[str, float]:
    """Pre-pooling stream volumes (fractions of whole-crude feed) at a severity.

    The quality model (features/quality.py) pools these with its per-stream
    quality vectors; ``yields_from_assay`` pools the same streams by volume.
    One mass balance, two consumers — no drift between yield and quality.

    Returns:
        Dict of stream → volume fraction of feed:
        light_naphtha, mid_naphtha (SR splits at 80 °C), reformate,
        reformer_lpg, isomerate (= light naphtha; named for clarity),
        fcc_gasoline, alkylate, fcc_gas_nonalk (fuel gas + coke + propylene),
        kero, sr_distillate, fcc_lco, vgo_slurry, residue.
    """
    curve = np.asarray(tbp_curve, dtype=float)
    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"severity must be in [0, 1], got {severity}")

    # Reuse the cut integrator: [naphtha, kero, diesel, vgo, residue]
    cuts = tbp_cut_fractions(curve)
    naphtha, kero, diesel_cut, vgo, residue = cuts
    light_nap = _interpolate_vol_pct(curve, LIGHT_NAPHTHA_END_C) / 100.0
    mid_nap = naphtha - light_nap

    conversion = FCC_CONVERSION_AT_S0 + severity * (FCC_CONVERSION_AT_S1 - FCC_CONVERSION_AT_S0)
    fcc_gasoline = vgo * conversion * FCC_GASOLINE_SHARE
    fcc_lco = vgo * conversion * FCC_LCO_SHARE
    fcc_gas_coke = vgo * conversion * FCC_GAS_COKE_SHARE
    slurry = vgo * (1.0 - conversion)

    # Octane units (fixed fractions — methodology.md §3b)
    butane_lpg = light_nap * BUTANE_PULL_SHARE
    light_nap_net = light_nap * (1.0 - BUTANE_PULL_SHARE)
    reformate = mid_nap * REFORMER_YIELD
    reformer_lpg = mid_nap * (1.0 - REFORMER_YIELD)
    alkylate = fcc_gas_coke * ALKYLATE_SHARE
    fcc_gas_nonalk = fcc_gas_coke * (1.0 - ALKYLATE_SHARE)

    return {
        "light_naphtha": light_nap_net,
        "mid_naphtha": mid_nap,
        "isomerate": light_nap_net * ISOM_YIELD,
        "reformate": reformate,
        "reformer_lpg": reformer_lpg,
        "fcc_gasoline": fcc_gasoline,
        "alkylate": alkylate,
        "fcc_gas_nonalk": fcc_gas_nonalk,
        "kero": kero,
        "sr_distillate": diesel_cut,
        "fcc_lco": fcc_lco,
        "vgo_slurry": slurry,
        "residue": residue,
        "butane_lpg": butane_lpg,
    }
