"""Cost-anchor tests — differential table sanity, strict coverage, offline
Brent loader (synthetic cache), and the committed artifact's integrity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dangote_opt.data.acquire import CATALOG, _cache_key, _facet_params
from dangote_opt.data.costs import (
    DIFFERENTIALS,
    build_crude_costs,
    load_brent_reference,
)

COSTS_PARQUET = Path("data/derived/costs_phase2.parquet")


def test_differential_table_covers_slate():
    from dangote_opt.data.assay_parsers import SLATE_SPECS

    assert {d.crude_id for d in DIFFERENTIALS} == {s["crude_id"] for s in SLATE_SPECS}
    assert all(d.status == "ASSUMED" for d in DIFFERENTIALS)  # nothing dressed as observed
    assert all(d.basis for d in DIFFERENTIALS)  # every assumption carries rationale


def test_differential_ordering_is_quality_consistent():
    d = {x.crude_id: x.diff_usd_bbl for x in DIFFERENTIALS}
    # Lightest sweet Nigerian commands the largest premium; sour grades discount.
    assert (
        d["qua_iboe"]
        > d["bonny_light"]
        > d["forcados"]
        > d["thunder_horse"]
        > d["alaska_north_slope"]
    )
    assert min(d.values()) < 0 < max(d.values())  # straddle Brent


def test_build_costs_maps_and_rounds():
    costs = build_crude_costs(["bonny_light", "alaska_north_slope"], 69.10)
    assert costs["bonny_light"] == pytest.approx(70.10)
    assert costs["alaska_north_slope"] == pytest.approx(66.60)


def test_build_costs_never_silently_defaults():
    with pytest.raises(KeyError, match="urals"):
        build_crude_costs(["bonny_light", "urals"], 70.0)


def test_load_brent_reference_offline_from_cache(tmp_path):
    """Write a synthetic Brent cache (correct cache-key layout) and load offline."""
    series = CATALOG["brent_spot"]
    query = {
        "frequency": series.frequency,
        "data[]": list(series.data_columns),
        **_facet_params(series.facets),
    }
    cache_path = tmp_path / f"{_cache_key(series.route, query)}.parquet"
    periods = [f"2024-{m:02d}" for m in range(1, 13)]
    values = np.linspace(70.0, 82.0, 12)  # mean = 76.0
    pd.DataFrame(
        {"period": periods, "value": values, "series": "RBRTE", "units": "$/BBL"}
    ).to_parquet(cache_path, index=False)

    ref, window = load_brent_reference(cache_dir=tmp_path, months=12)
    assert ref == pytest.approx(float(values.mean()))
    assert len(window) == 12
    assert str(window["period"].iloc[-1]) == "2024-12"


def test_load_brent_reference_end_period_filters(tmp_path):
    series = CATALOG["brent_spot"]
    query = {
        "frequency": series.frequency,
        "data[]": list(series.data_columns),
        **_facet_params(series.facets),
    }
    cache_path = tmp_path / f"{_cache_key(series.route, query)}.parquet"
    periods = [f"2024-{m:02d}" for m in range(1, 13)]
    pd.DataFrame(
        {"period": periods, "value": np.full(12, 75.0), "series": "RBRTE", "units": "$/BBL"}
    ).to_parquet(cache_path, index=False)
    ref, window = load_brent_reference(cache_dir=tmp_path, end_period="2024-06", months=6)
    assert ref == pytest.approx(75.0)
    assert len(window) == 6


def test_load_brent_reference_missing_cache_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="no API key"):
        load_brent_reference(cache_dir=tmp_path, months=12)


def test_load_brent_reference_short_window_raises(tmp_path):
    series = CATALOG["brent_spot"]
    query = {
        "frequency": series.frequency,
        "data[]": list(series.data_columns),
        **_facet_params(series.facets),
    }
    cache_path = tmp_path / f"{_cache_key(series.route, query)}.parquet"
    pd.DataFrame(
        {
            "period": ["2024-01", "2024-02"],
            "value": [75.0, 76.0],
            "series": "RBRTE",
            "units": "$/BBL",
        }
    ).to_parquet(cache_path, index=False)
    with pytest.raises(ValueError, match="need 12"):
        load_brent_reference(cache_dir=tmp_path, months=12)


def test_committed_costs_artifact_is_valid():
    assert COSTS_PARQUET.exists(), "run scripts/build_costs.py and commit the output"
    df = pd.read_parquet(COSTS_PARQUET)
    assert set(df["crude_id"]) == {d.crude_id for d in DIFFERENTIALS}
    assert (df["status"] == "ASSUMED").all()
    # costs = brent_ref + differential, recomputable from the sidecar
    sidecar = json.loads((COSTS_PARQUET.parent / "costs_phase2.json").read_text())
    brent_ref = sidecar["brent_reference_usd_bbl"]
    for _, row in df.iterrows():
        assert row["cost_usd_bbl"] == pytest.approx(
            brent_ref + row["differential_usd_bbl"], abs=0.011
        )
