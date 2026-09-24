"""Live market ticker feeds — Phase 6 (docs/data_provenance.md rows 2, 8).

Two free, keyless feeds for the dashboard ticker (spec §3.7 "live" credibility):

* **NGN/USD FX** — open.er-api.com ``/v6/latest/USD`` (provenance row 8,
  Exchangerate-API free tier, fair use). Response carries ``result: "success"``,
  ``time_last_update_utc`` and a flat ``rates`` mapping that includes ``NGN``.
  Verified live 2026-09-23.
* **WTI spot** — EIA v2 ``petroleum/pri/spt`` at **daily** frequency, product
  ``EPCWTI`` / process ``PF4`` / duoarea **``YCUOK``** (Cushing; probed live
  2026-09-23 — the only area the product carries on this route, like Brent's
  ``ZEU``). Native $/bbl, no unit transform. Goes through the same cache-first
  client as every other EIA series; offline fallback reads the largest cached
  pull via ``acquire.load_cached_series`` (sidecar-located — never reconstruct
  cache keys).

Cache discipline: FX responses are cached to disk for 1 hour (row 8 design) so
HF Space cold starts and repeated visits stay inside fair use. Every failure
mode degrades to a stale/staged value flagged ``stale=True`` — the ticker must
never break the dashboard, and never shows a live-looking number it cannot
back with a timestamp.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

FX_URL = "https://open.er-api.com/v6/latest/USD"
FX_CACHE_PATH = Path("data/raw/fx/latest_usd.json")
FX_CACHE_TTL_S = 3600  # provenance row 8: cache 1 h
FX_TIMEOUT_S = 15

Transport = Callable[..., requests.Response]  # injectable for tests


@dataclass(frozen=True)
class TickerQuote:
    """One ticker value with the timestamp that makes it auditable."""

    label: str
    value: float
    as_of: str  # source-provided timestamp string (UTC) or "staged artifact"
    source: str
    stale: bool


def _read_fx_cache(path: Path) -> dict[str, Any] | None:
    """Return the cached FX payload if present and fresh, else None (stale kept)."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched = float(payload.get("_fetched_monotonic", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if fetched <= 0 or (time.monotonic() - fetched) >= FX_CACHE_TTL_S:
        return None
    return payload


def _write_fx_cache(path: Path, payload: dict[str, Any]) -> None:
    """Persist the payload with a fetch stamp (monotonic clock — TTL only)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stamped = {**payload, "_fetched_monotonic": time.monotonic()}
    path.write_text(json.dumps(stamped), encoding="utf-8")


def fetch_ngn_usd_rate(
    cache_path: Path = FX_CACHE_PATH,
    *,
    transport: Transport = requests.get,
    refresh: bool = False,
) -> TickerQuote:
    """NGN per USD from open.er-api.com, disk-cached for 1 h.

    Returns a quote whose ``as_of`` is the provider's own update timestamp.
    Falls back to the stale cache (``stale=True``) on any network/parse failure;
    raises only when there is neither a live response nor any cache.
    """
    if not refresh:
        cached = _read_fx_cache(cache_path)
        if cached is not None:
            return TickerQuote(
                label="NGN/USD",
                value=float(cached["rates"]["NGN"]),
                as_of=str(cached.get("time_last_update_utc", "unknown")),
                source="open.er-api.com (cached)",
                stale=False,
            )
    try:
        resp = transport(FX_URL, timeout=FX_TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        stale = cache_path
        if stale.exists():
            prev = json.loads(stale.read_text(encoding="utf-8"))
            return TickerQuote(
                label="NGN/USD",
                value=float(prev["rates"]["NGN"]),
                as_of=str(prev.get("time_last_update_utc", "unknown")),
                source="open.er-api.com (stale cache)",
                stale=True,
            )
        raise RuntimeError(f"FX feed failed and no cache exists: {exc!r}") from exc
    if payload.get("result") != "success" or "NGN" not in payload.get("rates", {}):
        raise RuntimeError(f"FX feed returned unusable payload: {str(payload)[:200]}")
    _write_fx_cache(cache_path, payload)
    return TickerQuote(
        label="NGN/USD",
        value=float(payload["rates"]["NGN"]),
        as_of=str(payload.get("time_last_update_utc", "unknown")),
        source="open.er-api.com",
        stale=False,
    )


def fetch_wti_spot(
    api_key: str,
    *,
    refresh: bool = False,
    cache_dir: Path = Path("data/raw/eia"),
    transport: Transport = requests.get,
) -> TickerQuote:
    """Latest WTI spot ($/bbl) from the pinned daily EIA series (YCUOK).

    Cache-first through the shared EIA client; offline fallback reads the
    largest cached pull for the series key. Raises when no key is available
    AND no cache exists — callers decide how to render that.
    """
    from dangote_opt.data.acquire import CATALOG, fetch_eia_series, load_cached_series

    series = CATALOG["wti_spot_daily"]
    try:
        if api_key:
            df = fetch_eia_series(
                series, api_key, refresh=refresh, cache_dir=cache_dir, transport=transport
            )
        else:
            df = load_cached_series(series.key, cache_dir)
    except Exception:
        df = load_cached_series(series.key, cache_dir)  # last-resort offline read
    if df.empty:
        raise RuntimeError("WTI series has no rows (cache and live both empty)")
    latest = df.sort_values("period").iloc[-1]
    return TickerQuote(
        label="WTI spot",
        value=float(latest["value"]),
        as_of=str(latest["period"]),
        source="EIA v2 petroleum/pri/spt (EPCWTI, YCUOK, daily)",
        stale=not api_key,
    )
