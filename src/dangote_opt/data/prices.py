"""Product-price anchor — EIA USGC spot prices (provenance row 2 → objective).

Replaces ``CONFIG.default_prices`` for the three pools with real, verified
series (docs/data_provenance.md row 2, live-verified 2026-09-19):

* gasoline → Conventional Regular Gasoline spot ``EPMRU``  ($/gal)
* diesel   → ULSD (0–15 ppm) spot ``EPD2DXL0``             ($/gal)
* jet      → Kerosene-Type Jet Fuel spot ``EPJK``          ($/gal)

Unit transform: $/gal × 42 = $/bbl (documented Phase 2 transform, provenance
row 2) applied **here**, never at acquisition.

**Petrochem pool stays on ``CONFIG.default_prices["petrochem"]`` — a labeled
PLACEHOLDER, not real data.** Rationale: the pool is LPG + propylene + unconverted
residue/slurry + coke; no single EIA spot series represents that basket (probed
2026-09-19: no naphtha or RGC residual-fuel spot on EIA; ``pri/resid`` /
``pri/refoth`` are retail/wholesale by state, no Gulf-Coast monthly spot).
Refresh paths when a citable anchor is found: MW Spot for LPG (Platts — not
open), or a documented Brent-minus-discount convention like the crude
differentials (data/costs.py pattern).

Prices are trailing-window monthly averages (same convention as the Brent
cost anchor, data/costs.py) so the objective sees one stable number per pool.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dangote_opt.config import CONFIG
from dangote_opt.data.acquire import CATALOG, _cache_key, _facet_params, fetch_eia_series

GAL_PER_BBL = 42.0
DEFAULT_PRICE_WINDOW_MONTHS = 12

# CONFIG product order -> EIA product facet code on petroleum/pri/spt (RGC)
PRODUCT_SERIES: dict[str, str] = {
    "gasoline": "EPMRU",
    "diesel": "EPD2DXL0",
    "jet": "EPJK",
    # "petrochem" intentionally absent — PLACEHOLDER, see module docstring
}
PLACEHOLDER_PRODUCTS: tuple[str, ...] = ("petrochem",)


def usgc_prices_frame(
    api_key: str,
    *,
    cache_dir: Path = Path("data/raw/eia"),
    refresh: bool = False,
    start: str = "2015-01",
    end: str = "2025-12",
) -> pd.DataFrame:
    """Pull the three USGC spot series (cache-first) as one tidy frame."""
    series = CATALOG["us_product_prices"]
    return fetch_eia_series(
        series, api_key, start=start, end=end, cache_dir=cache_dir, refresh=refresh
    )


def product_prices(
    frame: pd.DataFrame,
    *,
    end_period: str | None = None,
    months: int = DEFAULT_PRICE_WINDOW_MONTHS,
) -> dict[str, float]:
    """Trailing-window mean price per pool in CONFIG product order [USD/bbl].

    Args:
        frame: tidy frame from ``usgc_prices_frame`` (columns: period, product,
            value in $/gal).
        end_period: last 'YYYY-MM' to include (default: latest).
        months: trailing window length (12 = annual anchor, matching costs).

    Returns:
        ``{product: usd_per_bbl}`` for every CONFIG product. Gasoline/diesel/jet
        come from EIA; ``petrochem`` carries the CONFIG placeholder (disclosed).
    """
    df = frame.copy()
    df["period"] = df["period"].astype(str)
    if end_period is not None:
        df = df[df["period"] <= end_period]
    # rows are monthly per product; take the trailing `months` rows of each
    recent = df.sort_values("period").groupby("product").tail(months)

    prices: dict[str, float] = {}
    for product, code in PRODUCT_SERIES.items():
        sub = recent[recent["product"] == code]
        if len(sub) < months:
            raise ValueError(
                f"need {months} months of {code} ({product}), found {len(sub)} — widen the pull"
            )
        prices[product] = round(float(sub["value"].mean()) * GAL_PER_BBL, 2)

    # Petrochem: disclosed placeholder — never presented as market data.
    for product in PLACEHOLDER_PRODUCTS:
        prices[product] = CONFIG.default_prices[product]

    # Return in CONFIG product order, every product present.
    return {p: prices[p] for p in CONFIG.products}


def prices_vector(frame: pd.DataFrame, **kwargs: object) -> list[float]:
    """``product_prices`` as a list in CONFIG product order (objective-ready)."""
    prices = product_prices(frame, **kwargs)  # type: ignore[arg-type]
    return [prices[p] for p in CONFIG.products]


def offline_cache_paths(cache_dir: Path = Path("data/raw/eia")) -> Path:
    """Parquet path of the us_product_prices pull (for offline consumers)."""
    series = CATALOG["us_product_prices"]
    query = {
        "frequency": series.frequency,
        "data[]": list(series.data_columns),
        **_facet_params(series.facets),
    }
    return cache_dir / f"{_cache_key(series.route, query)}.parquet"
