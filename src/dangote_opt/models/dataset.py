"""Surrogate training dataset — experiment design over the 5-crude slate.

Rows are synthetic blends sampled on the probability simplex × severity grid;
features are the **blend-weighted properties** the problem statement §3 names
(API, sulfur, severity) plus the blend-weighted TBP cut fractions (the bridge's
actual inputs — without them two blends with identical API/sulfur but different
curves would share features despite different yields). Labels are the Stage-1
bridge's 4-pool yields.

Design rule: the dataset is *generated from the cited bridge*, so label
provenance is methodology.md — no measured labels are claimed (spec §3.6).
Deterministic under ``DatasetSpec.seed``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from dangote_opt.features.bridge import tbp_cut_fractions, yields_from_assay

FloatArray = NDArray[np.float64]

FEATURE_COLUMNS = (
    "api_blend",
    "sulfur_blend",
    "severity",
    "cut_naphtha",
    "cut_kero",
    "cut_diesel",
    "cut_vgo",
    "cut_residue",
)
LABEL_COLUMNS = tuple(f"yield_{p}" for p in ("gasoline", "diesel", "jet", "petrochem"))


@dataclass(frozen=True)
class DatasetSpec:
    """Sampling design for the surrogate training set (all reproducible)."""

    n_samples: int = 4000
    seed: int = 20260919
    dirichlet_alpha: float = 0.55  # <1 → corner-seeking; blends stay diverse
    notes: str = ""


@dataclass(frozen=True)
class _Slate:
    """Immutable per-crude arrays extracted once from the slate artifact."""

    names: tuple[str, ...]
    apis: FloatArray
    sulfurs: FloatArray
    curves: tuple[FloatArray, ...]
    cut_fractions: FloatArray  # (5, 5): per-crude [nap, kero, diesel, vgo, resid]


def load_slate(parquet_path: str = "data/derived/slate_phase1.parquet") -> _Slate:
    """Load the committed Phase 1 slate into array form for sampling."""
    from dangote_opt.data.assays import frame_to_records

    records = frame_to_records(pd.read_parquet(parquet_path))
    curves = tuple(np.asarray(r.tbp_curve, dtype=float) for r in records)
    cuts = np.array([tbp_cut_fractions(c) for c in curves])
    return _Slate(
        names=tuple(r.name for r in records),
        apis=np.array([r.api for r in records], dtype=float),
        sulfurs=np.array([r.sulfur_pct for r in records], dtype=float),
        curves=curves,
        cut_fractions=cuts,
    )


def _sample_ratios(rng: np.random.Generator, spec: DatasetSpec, n_crudes: int) -> FloatArray:
    """Dirichlet samples on the simplex (corner-seeking keeps the boundary
    regions — where DE actually operates — well covered)."""
    return rng.dirichlet(np.full(n_crudes, spec.dirichlet_alpha), size=spec.n_samples)


def build_dataset(
    spec: DatasetSpec | None = None,
    slate: _Slate | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sample blends × severities and label them with the Stage-1 bridge.

    Args:
        spec: sampling design (seeded, deterministic).
        slate: pre-loaded slate; loaded from the committed artifact when None.

    Returns:
        (features, labels) DataFrames with ``FEATURE_COLUMNS`` /
        ``LABEL_COLUMNS``; one row per (sample, severity-grid) pair.
    """
    spec = spec or DatasetSpec()
    slate = slate or load_slate()
    n = slate.apis.size
    rng = np.random.default_rng(spec.seed)

    ratios = _sample_ratios(rng, spec, n)
    severities = rng.random(spec.n_samples)  # continuous severity per sample

    feat_rows: list[dict[str, float]] = []
    label_rows: list[dict[str, float]] = []
    for x, s in zip(ratios, severities, strict=True):
        api = float(x @ slate.apis)
        sulfur = float(x @ slate.sulfurs)
        blended_cuts = x @ slate.cut_fractions  # (5,)
        yields = np.zeros(4)
        for j, curve in enumerate(slate.curves):
            yields += x[j] * yields_from_assay(slate.apis[j], slate.sulfurs[j], curve, float(s))
        feat_rows.append(
            {
                "api_blend": api,
                "sulfur_blend": sulfur,
                "severity": float(s),
                **dict(zip(FEATURE_COLUMNS[3:], blended_cuts, strict=True)),
            }
        )
        label_rows.append(dict(zip(LABEL_COLUMNS, yields, strict=True)))

    return pd.DataFrame(feat_rows), pd.DataFrame(label_rows)
