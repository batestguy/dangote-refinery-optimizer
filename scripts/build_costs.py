"""Build the crude-cost anchor artifact — Brent reference + differentials.

Writes ``data/derived/costs_phase2.parquet`` (per-grade costs) and
``data/derived/costs_phase2.json`` (Brent reference + window + differential
table with ASSUMED status). Re-run after refreshing the Brent cache
(``scripts/eia_smoke.py`` or a wider ``fetch_eia_series`` pull).
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import dotenv_values  # noqa: E402

from dangote_opt.data.costs import (  # noqa: E402
    DEFAULT_COST_WINDOW_MONTHS,
    build_crude_costs,
    costs_frame,
    load_brent_reference,
)

DERIVED_DIR = Path("data/derived")


def main() -> int:
    key = dotenv_values(".env").get("EIA_API_KEY", "").strip() or None
    brent_ref, window = load_brent_reference(months=DEFAULT_COST_WINDOW_MONTHS, api_key=key)
    frame = costs_frame(brent_ref)
    costs = build_crude_costs(list(frame["crude_id"]), brent_ref)

    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(DERIVED_DIR / "costs_phase2.parquet", index=False)
    sidecar = {
        "artifact": "data/derived/costs_phase2.parquet",
        "generated": datetime.now(UTC).date().isoformat(),
        "brent_reference_usd_bbl": round(brent_ref, 2),
        "brent_window": {
            "months": DEFAULT_COST_WINDOW_MONTHS,
            "first": str(window["period"].iloc[0]),
            "last": str(window["period"].iloc[-1]),
            "series": "EIA RBRTE (petroleum/pri/spt, ZEU, PF4) — provenance row 2",
        },
        "differentials": frame.to_dict(orient="records"),
        "note": "differentials are ASSUMED quality-based values — refresh from OPEC MOMR",
    }
    (DERIVED_DIR / "costs_phase2.json").write_text(json.dumps(sidecar, indent=2))

    print(f"Brent reference (12-mo avg): ${brent_ref:.2f}/bbl")
    print(frame[["name", "differential_usd_bbl", "cost_usd_bbl"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
