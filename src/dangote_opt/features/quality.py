"""Blend-quality model — quality-spec constraints (spec §3.3, §4 decision 14).

Computes the four product-pool qualities from the bridge's component streams
(``features.bridge.component_volumes`` — one mass balance, two consumers) and
returns violations against the spec bundle in ``CONFIG``:

* gasoline RON           ≥ 91 (blended linearly by volume — octane numbers are
  themselves engine indices; linear volumetric blending is the LP-standard
  base rule per Gary & Handwerk ch. 10. The interactive Ethyl RT-70 scheme is
  the more accurate model but is not openly reproducible — traceability rule.)
* gasoline RVP           ≤ 60 kPa (RVP index blending: blend RVP^1.25 linearly,
  invert — the widely used psi^1.25 index, Haverly Systems, "Blending by
  Index" (2024) blog/HSI UDF docs)
* jet freeze point       ≤ −47 °C (linear, volume basis)
* diesel cetane index    ≥ 45 (linear, volume basis)

Every component quality is either (a) published on the vendor assay sheet
(TotalEnergies cut tables; ExxonMobil property rows — provenance row 3) or
(b) ASSUMED with a stated rationale, mirrored in docs/methodology.md §3c.
Nothing is invented silently.

Physical note (why the octane units exist): straight-run naphtha blends at
RON ≈ 58 — no real blend meets RON 91 without reforming/alkylation. The
bridge (methodology.md §3b) routes mid naphtha through a reformer (reformate
RON 98) and FCC gas through alkylation (RON 93); those constant product
qualities are cited in UNIT_QUALITIES below.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from dangote_opt.config import CONFIG
from dangote_opt.features.bridge import component_volumes

FloatArray = NDArray[np.float64]

RVP_EXPONENT = 1.25  # psi^1.25 index (Haverly, "Blending by Index")


# --- unit output qualities — cited ranges, docs/methodology.md §3c ----------
@dataclass(frozen=True)
class UnitQuality:
    """Quality of a conversion-unit output stream (constant, severity-free)."""

    ron: float | None = None  # None = stream not in gasoline pool
    rvp_kpa: float | None = None
    cetane_idx: float | None = None


UNIT_QUALITIES: dict[str, UnitQuality] = {
    # isomerate: light naphtha isomerization output, RON uplift 78→~82
    "isomerate": UnitQuality(ron=82.0, rvp_kpa=55.0),
    # reformate: C6+ naphtha reforming at high severity, RON 85–95+ → 98 end;
    # very low RVP (aromatic-rich, front end removed)
    "reformate": UnitQuality(ron=98.0, rvp_kpa=12.0),
    # FCC gasoline: RON 91–95 → 93 midpoint
    "fcc_gasoline": UnitQuality(ron=93.0, rvp_kpa=35.0),
    # alkylate: RON 90–98 → 93; very low RVP
    "alkylate": UnitQuality(ron=93.0, rvp_kpa=25.0),
    # FCC LCO: low-cetane diesel blendstock, cetane index ≈ 20–25
    "fcc_lco": UnitQuality(cetane_idx=22.0),
}


# --- per-crude component qualities (assay-derived; see module docstring) ----
@dataclass(frozen=True)
class CrudeQuality:
    """Per-crude qualities for the streams the quality model consumes.

    ``status`` fields document PUBLISHED vs ASSUMED per value — provenance
    rule: an assumption never travels under a published name.
    """

    crude_id: str
    light_naphtha_ron: float  # SR <80 °C naphtha (pre-reformer)
    kero_freeze_c: float  # SR kerosene 180–260 °C proxy cut
    sr_distillate_cetane: float  # SR diesel 260–360 °C proxy cut
    ron_status: str
    freeze_status: str
    cetane_status: str


CRUDE_QUALITIES: dict[str, CrudeQuality] = {
    # TotalEnergies sheets publish the values used (closest bracketing cut):
    #   RON: 15–80 °C light-naphtha cut; freeze: 150–250 kero cut;
    #   cetane: 230–375 gasoil cut (contains the 260–360 diesel cut).
    "bonny_light": CrudeQuality(
        "bonny_light",
        77.2,
        -56.0,
        45.2,
        "PUBLISHED (TE 15-80)",
        "PUBLISHED (TE 150-250)",
        "PUBLISHED (TE 230-375)",
    ),
    "forcados": CrudeQuality(
        "forcados",
        77.4,
        -56.0,
        45.2,
        "PUBLISHED (TE 15-80)",
        "PUBLISHED (TE 150-250)",
        "PUBLISHED (TE 230-375)",
    ),
    # ExxonMobil sheets: light-naphtha RON row is internally inconsistent in
    # extraction (MON > RON under every column alignment) → ASSUMED at typical
    # light paraffinic naphtha RON; freeze = midpoint of published kero-range
    # values; cetane = mid of published diesel-range values (column alignment
    # ambiguous in the flattened PDF grid — do not over-claim).
    "qua_iboe": CrudeQuality(
        "qua_iboe",
        78.0,
        -43.0,
        55.0,
        "ASSUMED (XOM row unusable)",
        "PUBLISHED kero-range mid",
        "ASSUMED (published 50–61, mid)",
    ),
    "alaska_north_slope": CrudeQuality(
        "alaska_north_slope",
        78.0,
        -50.0,
        50.0,
        "ASSUMED (XOM row unusable)",
        "PUBLISHED kero-range mid",
        "ASSUMED (published 46–51, mid)",
    ),
    "thunder_horse": CrudeQuality(
        "thunder_horse",
        78.0,
        -44.0,
        55.0,
        "ASSUMED (XOM row unusable)",
        "PUBLISHED kero-range mid",
        "ASSUMED (published 53–61, mid)",
    ),
}


# --- index blending helpers (docs/methodology.md §3c) -----------------------
def rvp_index(rvp_kpa: FloatArray) -> FloatArray:
    """psi^1.25 RVP index (Haverly). Vectorized over kPa values."""
    return np.power(np.asarray(rvp_kpa, dtype=float), RVP_EXPONENT)


def rvp_from_index(index: float) -> float:
    """Invert the psi^1.25 index back to kPa."""
    return float(index) ** (1.0 / RVP_EXPONENT)


def linear_blend(values: FloatArray, volumes: FloatArray) -> float:
    """Volume-weighted mean property (octane, cetane, freeze)."""
    volumes = np.asarray(volumes, dtype=float)
    total = float(volumes.sum())
    if total <= 0:
        raise ValueError("cannot blend quality over zero volume")
    return float(np.dot(values, volumes) / total)


def pool_qualities(components: dict[str, float], q: CrudeQuality) -> dict[str, float]:
    """Product-pool qualities for one crude's component streams.

    Args:
        components: volume fractions of feed from ``bridge.component_volumes``.
        q: the crude's component qualities.

    Returns:
        gasoline_ron, gasoline_rvp_kpa, jet_freeze_c, diesel_cetane_idx.
    """
    gas_streams = ("isomerate", "reformate", "fcc_gasoline", "alkylate")
    vols = np.array([components[s] for s in gas_streams])
    rons = np.array([UNIT_QUALITIES[s].ron for s in gas_streams])
    rvps = np.array([UNIT_QUALITIES[s].rvp_kpa for s in gas_streams])
    # isomerate RON comes from the crude's own light naphtha (+isom uplift);
    # the unit-output components use their constant cited qualities.
    rons[0] = q.light_naphtha_ron + (UNIT_QUALITIES["isomerate"].ron - 78.0)

    return {
        "gasoline_ron": linear_blend(rons, vols),
        "gasoline_rvp_kpa": rvp_from_index(linear_blend(rvp_index(rvps), vols)),
        "jet_freeze_c": q.kero_freeze_c,  # single-component pool
        "diesel_cetane_idx": linear_blend(
            np.array([q.sr_distillate_cetane, UNIT_QUALITIES["fcc_lco"].cetane_idx]),
            np.array([components["sr_distillate"], components["fcc_lco"]]),
        ),
    }


def blend_pool_qualities(
    ratios: FloatArray,
    curves: list[FloatArray],
    qualities: list[CrudeQuality],
    severity: float,
) -> dict[str, float]:
    """Blend-level pool qualities: volume-weighted across crudes and streams.

    Args:
        ratios: blend ratios (sum ≈ 1, non-negative).
        curves: one TBP curve per crude (same order).
        qualities: one CrudeQuality per crude (same order).
        severity: FCC severity proxy in [0, 1].

    Returns:
        gasoline_ron, gasoline_rvp_kpa, jet_freeze_c, diesel_cetane_idx for
        the blended refinery pools.
    """
    ratios = np.asarray(ratios, dtype=float)
    # Stream-level aggregation across crudes: pool the *streams* (exact mass
    # balance), then compute each pool's quality from its blended components.
    keys = (
        "isomerate",
        "reformate",
        "fcc_gasoline",
        "alkylate",
        "sr_distillate",
        "fcc_lco",
        "kero",
    )
    totals = {k: 0.0 for k in keys}
    light_ron_v: list[float] = []  # (volume, ron) pairs for isomerate RON
    freeze_v: list[tuple[float, float]] = []
    cetane_sr: list[tuple[float, float]] = []

    for x, curve, q in zip(ratios, curves, qualities, strict=True):
        comp = component_volumes(np.asarray(curve, dtype=float), severity)
        for k in keys:
            totals[k] += float(x) * comp[k]
        light_ron_v.append((float(x) * comp["isomerate"], q.light_naphtha_ron))
        freeze_v.append((float(x) * comp["kero"], q.kero_freeze_c))
        cetane_sr.append((float(x) * comp["sr_distillate"], q.sr_distillate_cetane))

    if totals["isomerate"] + totals["reformate"] + totals["fcc_gasoline"] + totals["alkylate"] <= 0:
        raise ValueError("gasoline pool is empty — cannot compute quality")
    if totals["sr_distillate"] + totals["fcc_lco"] <= 0:
        raise ValueError("diesel pool is empty — cannot compute quality")
    if totals["kero"] <= 0:
        raise ValueError("jet pool is empty — cannot compute quality")

    iso_ron = linear_blend(
        np.array([r for _, r in light_ron_v]), np.array([v for v, _ in light_ron_v])
    )
    gas_vols = np.array(
        [totals["isomerate"], totals["reformate"], totals["fcc_gasoline"], totals["alkylate"]]
    )
    gas_rons = np.array(
        [
            iso_ron + (UNIT_QUALITIES["isomerate"].ron - 78.0),
            UNIT_QUALITIES["reformate"].ron,
            UNIT_QUALITIES["fcc_gasoline"].ron,
            UNIT_QUALITIES["alkylate"].ron,
        ]
    )
    gas_rvps = np.array(
        [
            UNIT_QUALITIES["isomerate"].rvp_kpa,
            UNIT_QUALITIES["reformate"].rvp_kpa,
            UNIT_QUALITIES["fcc_gasoline"].rvp_kpa,
            UNIT_QUALITIES["alkylate"].rvp_kpa,
        ]
    )
    return {
        "gasoline_ron": linear_blend(gas_rons, gas_vols),
        "gasoline_rvp_kpa": rvp_from_index(linear_blend(rvp_index(gas_rvps), gas_vols)),
        "jet_freeze_c": linear_blend(
            np.array([f for _, f in freeze_v]), np.array([v for v, _ in freeze_v])
        ),
        "diesel_cetane_idx": linear_blend(
            np.array(
                [
                    linear_blend(
                        np.array([c for _, c in cetane_sr]),
                        np.array([v for v, _ in cetane_sr]),
                    ),
                    UNIT_QUALITIES["fcc_lco"].cetane_idx,
                ]
            ),
            np.array([totals["sr_distillate"], totals["fcc_lco"]]),
        ),
    }


def quality_violations(quals: dict[str, float]) -> list[str]:
    """Human-readable list of spec violations (empty = on-spec)."""
    violated: list[str] = []
    if quals["gasoline_ron"] < CONFIG.gasoline_ron_min:
        violated.append(f"gasoline RON {quals['gasoline_ron']:.1f} < {CONFIG.gasoline_ron_min}")
    if quals["gasoline_rvp_kpa"] > CONFIG.gasoline_rvp_kpa_max:
        violated.append(
            f"gasoline RVP {quals['gasoline_rvp_kpa']:.1f} kPa > {CONFIG.gasoline_rvp_kpa_max}"
        )
    if quals["jet_freeze_c"] > CONFIG.jet_freeze_point_c_max:
        violated.append(
            f"jet freeze {quals['jet_freeze_c']:.1f}°C > {CONFIG.jet_freeze_point_c_max}°C"
        )
    if quals["diesel_cetane_idx"] < CONFIG.diesel_cetane_min:
        violated.append(
            f"diesel cetane {quals['diesel_cetane_idx']:.1f} < {CONFIG.diesel_cetane_min}"
        )
    return violated


def quality_violation_magnitude(quals: dict[str, float]) -> float:
    """Σ (v + v²) over quality-spec violations (same form as the API/S penalty).

    Units differ per constraint (RON points, kPa, °C, cetane points) — each is
    O(1–10) in practice, and CONFIG.constraint_penalty scales the sum, matching
    the blend-property penalty treatment.
    """
    v = 0.0
    v += max(CONFIG.gasoline_ron_min - quals["gasoline_ron"], 0.0)
    v += max(quals["gasoline_rvp_kpa"] - CONFIG.gasoline_rvp_kpa_max, 0.0)
    v += max(quals["jet_freeze_c"] - CONFIG.jet_freeze_point_c_max, 0.0)
    v += max(CONFIG.diesel_cetane_min - quals["diesel_cetane_idx"], 0.0)
    return v + v * v
