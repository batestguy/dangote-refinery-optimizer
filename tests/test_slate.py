"""Slate build tests — parse the real vendor PDFs if present, always validate
the committed parquet artifact (data/derived/slate_phase1.parquet)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from dangote_opt.data.assay_parsers import SLATE_SPECS, build_slate
from dangote_opt.data.assays import frame_to_records, validate_slate

SLATE_PARQUET = Path("data/derived/slate_phase1.parquet")


def test_slate_builds_and_validates_from_pdfs():
    """Full parse test — requires the vendor PDFs in data/raw/assays/ (gitignored)."""
    if not Path("data/raw/assays/BONNY-LIGHT.pdf").exists():
        pytest.skip("vendor PDFs not downloaded (data/raw/ is gitignored)")
    records = build_slate()
    validate_slate(records, n_expected=5)


def test_committed_slate_parquet_is_valid():
    """The committed artifact must always exist and pass all validation."""
    assert SLATE_PARQUET.exists(), "run scripts/build_slate.py and commit the output"
    df = pd.read_parquet(SLATE_PARQUET)
    records = frame_to_records(df)
    validate_slate(records, n_expected=5)
    assert {r.crude_id for r in records} == {s["crude_id"] for s in SLATE_SPECS}


def test_slate_properties_are_physically_sane():
    """Whole-crude values must match published figures (interviewer-checkable)."""
    df = pd.read_parquet(SLATE_PARQUET).set_index("crude_id")
    # Spot-check against the vendor sheets (±0.2 API / ±0.03 wt-%).
    assert df.loc["bonny_light", "api"] == pytest.approx(34.9, abs=0.2)
    assert df.loc["bonny_light", "sulfur_pct"] == pytest.approx(0.15, abs=0.03)
    assert df.loc["forcados", "api"] == pytest.approx(31.5, abs=0.2)
    assert df.loc["qua_iboe", "api"] == pytest.approx(37.3, abs=0.2)
    assert df.loc["alaska_north_slope", "sulfur_pct"] == pytest.approx(1.04, abs=0.03)
    # Slate diversity: at least one crude above 1.0 wt-% sulfur (sour-ish) and
    # one below 0.2 (ultra-sweet) — otherwise the blend problem is trivial.
    assert (df["sulfur_pct"] > 1.0).any()
    assert (df["sulfur_pct"] < 0.2).any()


def test_slate_provenance_is_complete():
    df = pd.read_parquet(SLATE_PARQUET)
    assert df["source_url"].str.startswith("https://").all()
    assert df["source"].str.len().gt(0).all()
    assert df["pulled"].str.match(r"\d{4}-\d{2}-\d{2}").all()


def test_yields_basis_is_recorded_per_crude():
    """Mixing wt% and vol% bases silently would poison the Phase 2 bridge."""
    df = pd.read_parquet(SLATE_PARQUET)
    assert df["notes"].str.contains("yield basis").all()
