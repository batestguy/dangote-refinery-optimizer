"""Build the product-price artifact — EIA USGC spot averages per pool.

Writes ``data/derived/prices_phase2.parquet`` (per-product trailing-12-month
averages, $/gal and $/bbl, status REAL vs PLACEHOLDER) and
``data/derived/prices_phase2.json`` (sidecar: window, series IDs, unit
transform, petrochem disclosure). The committed artifact is the offline
fallback for the app when no EIA key/cache is available. Re-run after
refreshing the price cache (``scripts/eia_smoke.py`` or a wider pull).
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import dotenv_values  # noqa: E402

from dangote_opt.config import CONFIG  # noqa: E402
from dangote_opt.data.prices import (  # noqa: E402
    DEFAULT_PRICE_WINDOW_MONTHS,
    PRODUCT_SERIES,
    product_prices,
    usgc_prices_frame,
)

DERIVED_DIR = Path("data/derived")


def main() -> int:
    key = dotenv_values(".env").get("EIA_API_KEY", "").strip() or None
    if not key:
        raise SystemExit("EIA_API_KEY missing from .env — cannot build the price artifact")

    frame = usgc_prices_frame(key)
    prices = product_prices(frame, months=DEFAULT_PRICE_WINDOW_MONTHS)

    rows = []
    for product in CONFIG.products:
        is_real = product in PRODUCT_SERIES
        rows.append(
            {
                "product": product,
                "series": PRODUCT_SERIES.get(product, "PLACEHOLDER"),
                "price_usd_bbl": prices[product],
                "status": "REAL (EIA USGC spot, 12-mo avg)" if is_real else "PLACEHOLDER (CONFIG)",
            }
        )

    import pandas as pd

    out = pd.DataFrame(rows)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(DERIVED_DIR / "prices_phase2.parquet", index=False)
    sidecar = {
        "artifact": "data/derived/prices_phase2.parquet",
        "generated": datetime.now(UTC).date().isoformat(),
        "window_months": DEFAULT_PRICE_WINDOW_MONTHS,
        "unit_transform": "$/gal x 42 = $/bbl (EIA USGC spot series are $/gal)",
        "series": {
            "gasoline": "EPMRU (Conventional Regular Gasoline, RGC, PF4)",
            "diesel": "EPD2DXL0 (ULSD 0-15 ppm, RGC, PF4)",
            "jet": "EPJK (Kerosene-Type Jet Fuel, RGC, PF4)",
        },
        "prices_usd_bbl": prices,
        "disclosure": (
            "petrochem pool price is a PLACEHOLDER (CONFIG.default_prices) — no "
            "citable EIA spot series exists for the LPG/propylene/residue basket "
            "(probed 2026-09-19); refresh path documented in data/prices.py"
        ),
    }
    (DERIVED_DIR / "prices_phase2.json").write_text(json.dumps(sidecar, indent=2))

    print(f"Product prices (12-mo avg, USD/bbl): {prices}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
