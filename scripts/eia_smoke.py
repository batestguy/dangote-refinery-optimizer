"""Live EIA smoke test — run AFTER the API key lands in .env (Phase 1).

Not part of CI (no network, no secrets). Usage:

    uv run python scripts/eia_smoke.py            # uses .env EIA_API_KEY

For each catalog series it fetches a tiny window (2 monthly periods, US-level
facet only), prints row counts, and leaves the results cached under
data/raw/eia/ with provenance sidecars. Record the verified series/routes in
docs/data_provenance.md row 2 afterwards.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dangote_opt.data.acquire import CATALOG, EiaApiError, fetch_eia_series  # noqa: E402


def main() -> int:
    api_key = dotenv_values(".env").get("EIA_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        print("No EIA_API_KEY in .env — register free at https://www.eia.gov/opendata/")
        return 1

    failures = 0
    for key, series in CATALOG.items():
        try:
            df = fetch_eia_series(
                series,
                api_key,
                start="2024-01",
                end="2024-02",
                cache_dir=Path("data/raw/eia"),
            )
            print(f"OK  {key}: {len(df)} rows, cols={list(df.columns)}")
        except EiaApiError as exc:
            failures += 1
            print(f"FAIL {key}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
