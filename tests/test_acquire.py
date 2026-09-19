"""EIA client tests — fully offline via an injectable fake transport."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

from dangote_opt.data.acquire import (
    CATALOG,
    EiaApiError,
    EiaSeries,
    _cache_key,
    _facet_params,
    fetch_eia_series,
)


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200, text: str = ""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


def eia_payload(rows: list[dict[str, Any]], total: int | None = None, **extra: Any) -> dict:
    return {
        "response": {"total": str(total if total is not None else len(rows)), "data": rows},
        "apiVersion": "2.1.12",
        **extra,
    }


def make_transport(
    pages: list[list[dict[str, Any]]],
    capture: list[dict] | None = None,
    total: int | None = None,
):
    """Fake transport serving successive pages; records (url, params) per call.

    ``total`` overrides the echoed response.total (to simulate mismatched totals).
    """
    calls = {"n": 0}

    def transport(url: str, params: dict | None = None, timeout: float = 30) -> FakeResponse:
        if capture is not None:
            capture.append({"url": url, "params": dict(params or {})})
        page = pages[min(calls["n"], len(pages) - 1)]
        calls["n"] += 1
        return FakeResponse(eia_payload(page, total=total))

    return transport


SERIES = EiaSeries(
    key="test_series",
    route="petroleum/cons/test",
    data_columns=("value", "units"),
    frequency="monthly",
    facets={"duoarea": ("R1",)},
)


def row(period: str, value: str) -> dict[str, Any]:
    return {"period": period, "duoarea": "R1", "value": value, "units": "$/gal"}


def test_paginates_and_coerces_string_values(tmp_path):
    pages = [[row("2024-01", "2.50"), row("2024-02", "2.60")], [row("2024-03", "2.70")]]
    transport = make_transport(pages, total=3)
    df = fetch_eia_series(SERIES, "KEY", start="2024-01", end="2024-03",
                          cache_dir=tmp_path, transport=transport)
    assert len(df) == 3
    assert df["value"].dtype == "float64"
    assert df["value"].tolist() == [2.50, 2.60, 2.70]
    assert list(df["period"]) == ["2024-01", "2024-02", "2024-03"]
    assert df["units"].tolist() == ["$/gal"] * 3  # units descriptor stays string
    df = fetch_eia_series(SERIES, "KEY", start="2024-01", end="2024-03",
                          cache_dir=tmp_path, transport=transport)
    assert len(df) == 3
    assert df["value"].dtype == "float64"
    assert df["value"].tolist() == [2.50, 2.60, 2.70]
    assert list(df["period"]) == ["2024-01", "2024-02", "2024-03"]


def test_cache_hit_skips_network(tmp_path):
    pages = [[row("2024-01", "2.50")]]
    transport = make_transport(pages)
    df1 = fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=transport)
    # second call with a transport that would fail if called
    def broken(*a: Any, **k: Any) -> FakeResponse:
        raise AssertionError("network hit on cache path")
    df2 = fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=broken)
    pd.testing.assert_frame_equal(df1, df2)


def test_refresh_bypasses_cache(tmp_path):
    transport = make_transport([[row("2024-01", "2.50")]])
    fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=transport)
    calls: list[dict] = []
    transport2 = make_transport([[row("2024-01", "9.99")]], capture=calls)
    df = fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=transport2, refresh=True)
    assert df["value"].iloc[0] == 9.99
    assert len(calls) == 1


def test_sidecar_records_provenance_without_api_key(tmp_path):
    transport = make_transport([[row("2024-01", "2.50")]])
    fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=transport, start="2024-01")
    sidecars = list(tmp_path.glob("*.json"))
    assert len(sidecars) == 1
    text = sidecars[0].read_text()
    assert "KEY" not in text  # api key never persisted
    meta = json.loads(text)
    assert meta["route"].startswith("https://api.eia.gov/v2/")
    assert meta["series_key"] == "test_series"
    assert meta["rows"] == 1
    assert "pull_date" in meta and "params" in meta


def test_cache_key_is_deterministic_and_param_sensitive(tmp_path):
    params = {"frequency": "monthly", "data[]": ["value"]}
    k1 = _cache_key("route/a", params)
    k2 = _cache_key("route/a", dict(params))
    k3 = _cache_key("route/a", {**params, "start": "2024-01"})
    assert k1 == k2 and k1 != k3


def test_http_error_raises(tmp_path):
    def transport(url: str, params=None, timeout=30) -> FakeResponse:
        return FakeResponse({}, status_code=403, text="forbidden")

    with pytest.raises(EiaApiError, match="403"):
        fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=transport)


def test_error_payload_raises(tmp_path):
    def transport(url: str, params=None, timeout=30) -> FakeResponse:
        return FakeResponse({"error": "Invalid frequency 'weekly'", "code": 400})

    with pytest.raises(EiaApiError, match="Invalid frequency"):
        fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=transport)


def test_empty_api_key_raises(tmp_path):
    with pytest.raises(EiaApiError, match="key is empty"):
        fetch_eia_series(SERIES, "", cache_dir=tmp_path, transport=make_transport([]))


def test_length_over_cap_raises():
    with pytest.raises(ValueError, match="cap"):
        fetch_eia_series(SERIES, "KEY", length=5001, transport=make_transport([]))


def test_pagination_exhaustion_raises(tmp_path):
    # total=7 but every page repeats the same 2 rows -> never catches up
    transport = make_transport(
        [[row("2024-01", "2.50"), row("2024-02", "2.60")]], total=7
    )
    with pytest.raises(EiaApiError, match="pagination exhausted"):
        fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=transport, max_pages=3)


def test_facet_encoding():
    encoded = _facet_params({"product": ("GAS", "DIO"), "duoarea": ("R1",)})
    assert encoded == {
        "facets[duoarea][]": ["R1"],
        "facets[product][]": ["GAS", "DIO"],
    }


def test_facets_reach_request_url(tmp_path):
    capture: list[dict] = []
    transport = make_transport([[row("2024-01", "2.50")]], capture=capture)
    fetch_eia_series(SERIES, "KEY", cache_dir=tmp_path, transport=transport,
                     facets={"product": ("GAS",)})
    sent = capture[0]["params"]
    assert sent["facets[duoarea][]"] == ["R1"]
    assert sent["facets[product][]"] == ["GAS"]
    assert sent["api_key"] == "KEY"
    assert sent["frequency"] == "monthly"
    assert "/data" in capture[0]["url"]


def test_catalog_covers_phase1_needs():
    assert {"us_product_prices", "us_refinery_inputs", "us_crude_imports"} <= set(CATALOG)
    for s in CATALOG.values():
        assert s.route and s.data_columns and s.key == next(
            k for k, v in CATALOG.items() if v is s
        )
