"""Ticker feed tests — fully offline via injectable transports (Phase 6).

Covers the NGN/USD FX cache lifecycle (fresh → cached → stale → dead) and the
WTI daily series through the shared EIA client, plus the catalog pin itself.
"""

from __future__ import annotations

import json
import time
from typing import Any

import pandas as pd
import pytest
import requests

from dangote_opt.data.acquire import CATALOG
from dangote_opt.data.ticker import (
    FX_CACHE_TTL_S,
    fetch_ngn_usd_rate,
    fetch_wti_spot,
)


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code != 200:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def fx_payload() -> dict[str, Any]:
    return {
        "result": "success",
        "provider": "https://www.exchangerate-api.com",
        "time_last_update_utc": "Wed, 23 Sep 2026 00:02:31 +0000",
        "base_code": "USD",
        "rates": {"USD": 1.0, "EUR": 0.85, "NGN": 1328.371271},
    }


def eia_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "response": {"total": str(len(rows)), "data": rows},
        "apiVersion": "2.1.12",
    }


class FakeFXTransport:
    """Serves one canned FX payload (or raises); counts calls."""

    def __init__(self, payload: dict[str, Any] | None = None, exc: Exception | None = None):
        self.payload = payload if payload is not None else fx_payload()
        self.exc = exc
        self.calls = 0

    def __call__(self, url: str, timeout: float = 15) -> FakeResponse:
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return FakeResponse(self.payload)


class FakeEiaTransport:
    """Serves one canned EIA v2 page; records params for facet assertions."""

    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.params: list[dict] = []

    def __call__(self, url: str, params: dict | None = None, timeout: float = 30) -> FakeResponse:
        self.params.append(dict(params or {}))
        return FakeResponse(eia_payload(self.rows))


# ---------------------------------------------------------------- FX: happy path
def test_fx_live_fetch_parses_and_caches(tmp_path):
    transport = FakeFXTransport()
    cache = tmp_path / "fx.json"

    quote = fetch_ngn_usd_rate(cache, transport=transport)

    assert quote.label == "NGN/USD"
    assert quote.value == pytest.approx(1328.371271)
    assert quote.as_of == "Wed, 23 Sep 2026 00:02:31 +0000"
    assert quote.stale is False
    assert transport.calls == 1
    # Payload persisted with the monotonic fetch stamp (TTL bookkeeping only).
    cached = json.loads(cache.read_text(encoding="utf-8"))
    assert cached["rates"]["NGN"] == pytest.approx(1328.371271)
    assert cached["_fetched_monotonic"] > 0


# ---------------------------------------------------------------- FX: cache hit
def test_fx_cache_hit_skips_network(tmp_path):
    cache = tmp_path / "fx.json"
    payload = {**fx_payload(), "_fetched_monotonic": time.monotonic()}
    cache.write_text(json.dumps(payload), encoding="utf-8")
    transport = FakeFXTransport()

    quote = fetch_ngn_usd_rate(cache, transport=transport)

    assert transport.calls == 0  # cache-first: network never touched
    assert quote.value == pytest.approx(1328.371271)
    assert quote.stale is False
    assert "cached" in quote.source


# ---------------------------------------------------------------- FX: stale fallback
def test_fx_stale_cache_used_when_live_fails(tmp_path):
    cache = tmp_path / "fx.json"
    # Written WITHOUT a fresh stamp -> _read_fx_cache treats it as expired.
    cache.write_text(json.dumps(fx_payload()), encoding="utf-8")
    transport = FakeFXTransport(exc=requests.ConnectionError("network down"))

    quote = fetch_ngn_usd_rate(cache, transport=transport)

    assert quote.value == pytest.approx(1328.371271)
    assert quote.stale is True
    assert "stale" in quote.source


def test_fx_raises_when_no_cache_and_live_fails(tmp_path):
    transport = FakeFXTransport(exc=requests.ReadTimeout("timeout"))
    with pytest.raises(RuntimeError, match="no cache exists"):
        fetch_ngn_usd_rate(tmp_path / "missing.json", transport=transport)


# ---------------------------------------------------------------- FX: bad payloads
def test_fx_rejects_unusable_payload(tmp_path):
    transport = FakeFXTransport(payload={"result": "error", "rates": {}})
    with pytest.raises(RuntimeError, match="unusable payload"):
        fetch_ngn_usd_rate(tmp_path / "fx.json", transport=transport)


def test_fx_rejects_missing_ngn_rate(tmp_path):
    payload = fx_payload()
    payload["rates"] = {"USD": 1.0}  # NGN absent
    transport = FakeFXTransport(payload=payload)
    with pytest.raises(RuntimeError, match="unusable payload"):
        fetch_ngn_usd_rate(tmp_path / "fx.json", transport=transport)


# ---------------------------------------------------------------- WTI via EIA client
WTI_ROWS = [
    {"period": "2026-09-14", "value": "101.27", "duoarea": "YCUOK", "product": "EPCWTI"},
    {"period": "2026-09-15", "value": "107.02", "duoarea": "YCUOK", "product": "EPCWTI"},
]


def test_wti_live_fetch_uses_pinned_facets(tmp_path):
    transport = FakeEiaTransport(WTI_ROWS)

    quote = fetch_wti_spot("fake-key", cache_dir=tmp_path, transport=transport)

    assert quote.label == "WTI spot"
    assert quote.value == pytest.approx(107.02)
    assert quote.as_of == "2026-09-15"  # latest period, not first row
    assert quote.stale is False
    sent = transport.params[0]
    assert sent["facets[product][]"] == ["EPCWTI"]
    assert sent["facets[duoarea][]"] == ["YCUOK"]
    assert sent["frequency"] == "daily"
    assert sent["api_key"] == "fake-key"


def test_wti_offline_cache_read_without_key(tmp_path):
    # Sidecar-located cache (the acquire.load_cached_series convention).
    df = pd.DataFrame({"period": ["2026-09-14", "2026-09-15"], "value": [101.27, 107.02]})
    df.to_parquet(tmp_path / "cached.parquet", index=False)
    (tmp_path / "cached.json").write_text(
        json.dumps({"series_key": "wti_spot_daily", "rows": 2}), encoding="utf-8"
    )

    quote = fetch_wti_spot("", cache_dir=tmp_path)

    assert quote.value == pytest.approx(107.02)
    assert quote.stale is True  # no key -> cannot claim live


def test_wti_raises_without_key_and_cache(tmp_path):
    with pytest.raises(FileNotFoundError):
        fetch_wti_spot("", cache_dir=tmp_path)


# ---------------------------------------------------------------- catalog pin
def test_wti_series_pinned_in_catalog():
    series = CATALOG["wti_spot_daily"]
    assert series.route == "petroleum/pri/spt"
    assert series.frequency == "daily"
    assert series.facets["product"] == ("EPCWTI",)
    assert series.facets["duoarea"] == ("YCUOK",)
    assert FX_CACHE_TTL_S == 3600  # provenance row 8 design: cache 1 h
