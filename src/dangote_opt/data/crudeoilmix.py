"""CrudeOilMix (HF) mix_json mapper + streaming access — Phase 1.

Schema verified 2026-09-18 (docs/data_provenance.md row 1): top-level columns are
``oilid, n_components, is_blend, mix_json``; all assay detail is nested inside
``mix_json``. This module is deliberately **tolerant of unknown inner keys**
(the dataset card's flat modality names, e.g. ``wc_ent``, are NOT top-level and
the nested schema may vary by row): mapping happens by key-suffix heuristics with
explicit unknown-key surfacing, never silent guessing — unparseable rows are
returned in a reject frame with the reason, per the provenance doc's
flag-and-document rule.

Role guard (spec §3.1/§3.3): CrudeOilMix is the **gap-filler** for missing
TBP/property fields and the Nigerian-subset sanity check. It never trains the
surrogate directly (simulator-generated labels) and never bulk-downloads
(minimal-first, spec §4 row 6) — streaming only.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

HF_DATASET_ID = "anon12-neurips-2026/CrudeOilMix"

TOP_LEVEL_COLUMNS = ("oilid", "n_components", "is_blend", "mix_json")

# Canonical field <- inner-key word segments. A key maps if any segment equals
# the suffix (e.g. "sulfur_wt_pct" -> segments {sulfur, wt, pct} -> sulfur_pct)
# or the whole lowercased key ends with it (e.g. "wholecrudeapi"). Matched in
# order, so more specific suffixes come first.
_PROPERTY_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("sulfur", "sulfur_pct"),
    ("sulphur", "sulfur_pct"),
    ("tbp", "tbp_curve"),
    ("boiling", "tbp_curve"),
    ("distillation", "tbp_curve"),
    ("gravity", "api"),
    ("api", "api"),
)

# Whole-crude rows only (blends have n_components > 1 and are not assay records).
_WHOLE_CRUDE_MAX_COMPONENTS = 1


@dataclass(frozen=True)
class MixRowMapping:
    """Result of mapping one streamed row."""

    oilid: str
    properties: dict[str, Any]
    unmapped_keys: tuple[str, ...]


def map_mix_row(
    row: Mapping[str, Any],
    *,
    strict: bool = False,
) -> MixRowMapping:
    """Map one CrudeOilMix row to canonical property names.

    Args:
        row: dict with at least ``oilid`` and ``mix_json`` (str or dict).
        strict: if True, raise on unknown mix_json keys instead of collecting them.

    Returns:
        MixRowMapping with canonical ``api``/``sulfur_pct``/``tbp_curve`` where found.

    Raises:
        KeyError: row lacks ``oilid``/``mix_json``.
        ValueError: strict mode with unmapped keys, or unparseable mix_json.
    """
    if "oilid" not in row or "mix_json" not in row:
        raise KeyError(f"row missing 'oilid'/'mix_json': keys={sorted(row.keys())}")
    oilid = str(row["oilid"])
    raw = row["mix_json"]
    if isinstance(raw, str):
        try:
            inner = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{oilid}: mix_json is not valid JSON: {exc}") from exc
    elif isinstance(raw, Mapping):
        inner = dict(raw)
    else:
        raise ValueError(f"{oilid}: mix_json is {type(raw).__name__}, expected str/dict")

    properties: dict[str, Any] = {}
    unmapped: list[str] = []
    for key, value in inner.items():
        lowered = key.lower()
        segments = {seg for seg in re.split(r"[^a-z0-9]+", lowered) if seg}
        for suffix, canonical in _PROPERTY_SUFFIXES:
            if suffix in segments or lowered.endswith(suffix):
                properties.setdefault(canonical, value)
                break
        else:
            unmapped.append(key)
    if strict and unmapped:
        raise ValueError(f"{oilid}: unmapped mix_json keys {unmapped}")
    return MixRowMapping(oilid=oilid, properties=properties, unmapped_keys=tuple(unmapped))


def map_streamed_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map a stream of rows into (properties frame, rejects frame).

    Rejects keep the oilid + reason per the provenance doc's flag-and-document
    rule; they are never silently dropped.
    """
    good: list[dict[str, Any]] = []
    rejects: list[dict[str, str]] = []
    for row in rows:
        try:
            mapped = map_mix_row(row)
        except (KeyError, ValueError) as exc:
            rejects.append({"oilid": str(row.get("oilid", "<missing>")), "reason": str(exc)})
            continue
        good.append({"oilid": mapped.oilid, **mapped.properties})
    return pd.DataFrame(good), pd.DataFrame(rejects, columns=["oilid", "reason"])


def stream_whole_crudes(
    n: int | None = None,
    *,
    split: str = "train",
) -> list[dict[str, Any]]:
    """Stream whole-crude rows (n_components <= 1) from HF — never bulk-download.

    Args:
        n: stop after collecting this many whole-crude rows (None = whole split).
        split: HF split name.

    Returns:
        Raw row dicts (oilid, n_components, is_blend, mix_json as dict).
    """
    from datasets import load_dataset  # heavy import kept lazy

    ds = load_dataset(HF_DATASET_ID, split=split, streaming=True)
    collected: list[dict[str, Any]] = []
    skipped = 0
    for row in ds:
        # Structurally malformed rows can never be mapped — skip and count them
        # (map_streamed_rows is the reject-tracking path for parseable rows).
        if "oilid" not in row or "mix_json" not in row:
            skipped += 1
            continue
        try:
            n_components = int(row.get("n_components", 0))
        except (TypeError, ValueError):
            skipped += 1
            continue
        if n_components > _WHOLE_CRUDE_MAX_COMPONENTS:
            continue
        collected.append(dict(row))
        if n is not None and len(collected) >= n:
            break
    logger.info(
        "streamed %d whole-crude rows from %s (skipped %d malformed)",
        len(collected), HF_DATASET_ID, skipped,
    )
    return collected


def load_mix_json_parquet(path: str) -> pd.DataFrame:
    """Read a cached parquet of CrudeOilMix rows (columns: TOP_LEVEL_COLUMNS)."""
    df = pd.read_parquet(path)
    missing = [c for c in TOP_LEVEL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"parquet {path} missing CrudeOilMix columns: {missing}")
    return df
