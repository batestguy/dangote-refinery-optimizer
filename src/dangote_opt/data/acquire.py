"""EIA Open Data v2 client — Phase 1 (docs/data_provenance.md row 2).

Route/param contract verified against the official API guide
(https://www.eia.gov/opendata/documentation.php, read 2026-09-19):

* Data: ``GET https://api.eia.gov/v2/{route}/data`` with ``api_key`` (must be in
  the URL), ``frequency``, ``data[]`` column selection, ``facets[name][]=value``
  filters, ``start``/``end`` period bounds, and ``offset``/``length`` pagination.
* At most 5,000 rows per page; ``response.total`` echoes the matched row count.
* Since v2.1.6 all data values are JSON **strings** — coerced to float here.
* Facet columns are echoed back in every row (e.g. ``duoarea``, ``product``).
* API errors come back as JSON ``{"error": ..., "code": ...}`` with a matching
  HTTP status (consistent since v2.1.10).

Cache-first discipline (docs/data_provenance.md data-quality rules): a cache hit
skips the network entirely; a miss streams pages straight to parquet under
``data/raw/eia/`` and writes a provenance sidecar JSON (URL *without* the key,
params, pull date, row count, API version).
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.eia.gov/v2/"
PAGE_LENGTH_MAX = 5000  # API hard cap; consider constraining with facets/start/end
REQUEST_TIMEOUT_S = 30
# Data columns that EIA returns as descriptive strings (e.g. "$/gal") — never
# coerced to numeric. Everything else requested via data[] is coerced.
NON_NUMERIC_COLUMNS = frozenset({"units"})

Transport = Callable[..., requests.Response]  # injectable for tests


class EiaApiError(RuntimeError):
    """EIA API returned an error response or an unusable payload."""


@dataclass(frozen=True)
class EiaSeries:
    """A pinned EIA v2 pull. ``key`` is the stable local name used in caches."""

    key: str
    route: str
    data_columns: tuple[str, ...]
    facets: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    frequency: str = "monthly"
    notes: str = ""


# Series catalog — all routes/facets VERIFIED LIVE 2026-09-19 (see
# docs/data_provenance.md row 2 for pull dates and the smoke script output).
CATALOG: dict[str, EiaSeries] = {
    # US Gulf Coast product spot prices (PADD 3 — closest free analog to the
    # export-market pricing a Dangote-scale refinery sees). $/gal; convert to
    # $/bbl (×42) as a documented Phase 2 transform, never at acquisition.
    # Same route also carries WTI/Brent crude spots ($/bbl: EPCWTI/EPCBRENT).
    "us_product_prices": EiaSeries(
        key="us_product_prices",
        route="petroleum/pri/spt",
        data_columns=("value",),
        frequency="monthly",
        facets={
            "product": ("EPMRU", "EPD2DXL0", "EPJK"),  # gasoline / ULSD / jet
            "duoarea": ("RGC",),  # U.S. Gulf Coast
            "process": ("PF4",),  # Spot Price FOB
        },
        notes="Verified 2026-09-19: USGC spot $/gal (EER_EPMRU/EPD2DXL0/EPJK_PF4_RGC_DPG)",
    ),
    # Refinery utilization inputs: utilization = net crude input / operable
    # capacity (capacity itself comes from a separate capacity series/route).
    "us_refinery_inputs": EiaSeries(
        key="us_refinery_inputs",
        route="petroleum/sum/snd",
        data_columns=("value",),
        frequency="monthly",
        facets={
            "product": ("EPC0",),  # Crude Oil
            "process": ("YIR",),  # Refinery and Blender Net Input
            "duoarea": ("NUS",),  # U.S. total (NUS-Z00 has no YIR rows — verified)
        },
        notes="Verified 2026-09-19: US refinery net crude input (thousand bbl; MCRRIP*)",
    ),
    # Crude imports by country of origin — Nigerian volumes (NUS-NNI) anchor the
    # delivered-slate cost texture alongside provenance row 9 (Bonny Light spot).
    "us_crude_imports": EiaSeries(
        key="us_crude_imports",
        route="petroleum/move/impcus",
        data_columns=("value",),
        frequency="monthly",
        facets={
            "product": ("EPC0",),  # Crude Oil
            "process": ("IM0",),  # Imports
            "duoarea": ("NUS-NNI",),  # Nigeria (drop this facet for all origins)
        },
        notes="Verified 2026-09-19: US crude imports from Nigeria (thousand bbl/d)",
    ),
}


def _utc_today() -> str:
    """Pull date for provenance sidecars (module-level for test injection)."""
    return datetime.now(UTC).date().isoformat()


def _cache_key(route: str, params: Mapping[str, object]) -> str:
    """Deterministic key from route + params (api_key excluded by callers)."""
    payload = json.dumps({"route": route, "params": params}, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def _facet_params(facets: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    """Encode facets as EIA expects: facets[name][]=value (repeated keys)."""
    return {f"facets[{name}][]": list(values) for name, values in sorted(facets.items())}


def _eia_get(
    route: str,
    params: Mapping[str, object],
    api_key: str,
    transport: Transport,
) -> dict:
    """One GET against ``{BASE_URL}{route}/data``; returns the parsed payload."""
    url = f"{BASE_URL}{route}/data"
    full: dict[str, object] = {"api_key": api_key, **params}
    try:
        resp = transport(url, params=full, timeout=REQUEST_TIMEOUT_S)
    except requests.RequestException as exc:  # network-level failure
        raise EiaApiError(f"EIA request failed for {route}: {exc!r}") from exc
    if resp.status_code != 200:
        raise EiaApiError(f"EIA HTTP {resp.status_code} for {route}: {resp.text[:300]}")
    try:
        payload = resp.json()
    except ValueError as exc:
        raise EiaApiError(f"EIA returned non-JSON for {route}: {resp.text[:300]}") from exc
    if "error" in payload:
        raise EiaApiError(f"EIA error for {route}: {payload['error']}")
    return payload


def _coerce_value_columns(df: pd.DataFrame, data_columns: Iterable[str]) -> pd.DataFrame:
    """EIA v2 returns values as strings (v2.1.6) — coerce numeric columns to float.

    Non-numeric columns (units descriptors) are left as strings; a requested
    numeric column that fails coercion raises rather than passing silently.
    """
    for col in data_columns:
        if col in df.columns and col not in NON_NUMERIC_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="raise")
    return df


def fetch_eia_series(
    series: EiaSeries,
    api_key: str,
    *,
    start: str | None = None,
    end: str | None = None,
    facets: Mapping[str, Iterable[str]] | None = None,
    data_columns: Iterable[str] | None = None,
    frequency: str | None = None,
    length: int = PAGE_LENGTH_MAX,
    max_pages: int = 5,
    cache_dir: Path = Path("data/raw/eia"),
    refresh: bool = False,
    transport: Transport = requests.get,
) -> pd.DataFrame:
    """Fetch one EIA v2 series window, cache-first, as a tidy DataFrame.

    Args:
        series: pinned series (route + default facets/columns) from CATALOG.
        api_key: EIA_API_KEY value (never written to cache or sidecar).
        start/end: period bounds in the route's date format (e.g. '2020-01').
        facets: extra/overriding facet filters; merged over series defaults.
        data_columns: value columns to request; defaults to series.data_columns.
        frequency: override series.frequency (must be valid for the route).
        length: page size (API cap 5,000).
        max_pages: hard stop to avoid runaway pagination on surprise filters.
        cache_dir: parquet cache location (``data/raw/`` is gitignored).
        refresh: bypass the cache read (still rewrites it).
        transport: HTTP callable; inject a fake in tests.

    Returns:
        DataFrame with the requested data columns + echoed facet columns
        (+ ``period``). Cached as ``{cache_key}.parquet`` with a JSON sidecar.

    Raises:
        EiaApiError: HTTP/JSON/pagination failures, or pages exhausted before
            ``response.total`` rows were read.
    """
    if not api_key:
        raise EiaApiError("EIA API key is empty — set EIA_API_KEY in .env")
    if length > PAGE_LENGTH_MAX:
        raise ValueError(f"length {length} exceeds API cap {PAGE_LENGTH_MAX}")

    cols = tuple(data_columns) if data_columns else series.data_columns
    merged_facets: dict[str, tuple[str, ...]] = {k: tuple(v) for k, v in series.facets.items()}
    for k, v in (facets or {}).items():
        merged_facets[k] = tuple(v)

    query: dict[str, object] = {
        "frequency": frequency or series.frequency,
        "data[]": list(cols),
        **_facet_params(merged_facets),
    }
    if start is not None:
        query["start"] = start
    if end is not None:
        query["end"] = end

    key = _cache_key(series.route, query)
    cache_path = cache_dir / f"{key}.parquet"
    sidecar_path = cache_dir / f"{key}.json"
    if cache_path.exists() and not refresh:
        logger.info("EIA cache hit: %s", cache_path)
        return pd.read_parquet(cache_path)

    frames: list[pd.DataFrame] = []
    offset = 0
    total: int | None = None
    api_version = None
    for _ in range(max_pages):
        payload = _eia_get(
            series.route, {**query, "offset": offset, "length": length}, api_key, transport
        )
        response = payload.get("response", {})
        rows = response.get("data", [])
        frames.append(pd.DataFrame(rows))
        offset += len(rows)
        total = int(response.get("total", offset))
        api_version = payload.get("apiVersion", api_version)
        if warning := payload.get("warning"):
            logger.warning("EIA warning on %s: %s", series.route, warning)
        if not rows or offset >= total:
            break
    else:
        raise EiaApiError(
            f"pagination exhausted at max_pages={max_pages} for {series.route}: "
            f"read {offset} of {total} rows — narrow start/end or facets"
        )

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df = _coerce_value_columns(df, cols)
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    sidecar = {
        "route": f"{BASE_URL}{series.route}/data",
        "series_key": series.key,
        "params": {k: v for k, v in query.items()},  # api_key never included
        "pull_date": _utc_today(),
        "rows": len(df),
        "api_version": api_version,
        "notes": series.notes,
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2, default=str))
    logger.info("EIA pull cached: %s rows -> %s", len(df), cache_path)
    return df
