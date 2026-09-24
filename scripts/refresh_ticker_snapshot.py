"""Refresh the live-ticker snapshot artifact — Phase 6.

Pulls the two ticker feeds (NGN/USD FX + WTI spot) and writes
``data/derived/ticker_latest.json`` — the committed, cold-start-safe fallback
the marimo app renders when live feeds are unreachable (HF Space offline
start, rate limits, network flakes). Mirrors scripts/build_costs.py.

Re-run to refresh the snapshot (e.g. before each deploy); the app's live
attempt takes precedence whenever it succeeds.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import dotenv_values  # noqa: E402

from dangote_opt.data.ticker import fetch_ngn_usd_rate, fetch_wti_spot  # noqa: E402

DERIVED_DIR = Path("data/derived")
SNAPSHOT_PATH = DERIVED_DIR / "ticker_latest.json"


def main() -> int:
    key = dotenv_values(".env").get("EIA_API_KEY", "").strip()
    quotes = {}
    failures = []

    for name, fn in (
        ("ngn_usd", lambda: fetch_ngn_usd_rate(refresh=True)),
        ("wti_spot", lambda: fetch_wti_spot(key, refresh=True)),
    ):
        try:
            q = fn()
            quotes[name] = {
                "label": q.label,
                "value": q.value,
                "as_of": q.as_of,
                "source": q.source,
                "stale": q.stale,
            }
        except Exception as exc:  # noqa: BLE001 — one dead feed must not kill the snapshot
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            quotes[name] = None

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "artifact": "data/derived/ticker_latest.json",
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "quotes": quotes,
        "failures": failures,
    }
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    print(f"Snapshot written: {SNAPSHOT_PATH}")
    for name, q in quotes.items():
        if q:
            print(f"  {q['label']}: {q['value']:,.3f} (as of {q['as_of']}, stale={q['stale']})")
        else:
            print(f"  {name}: FAILED — {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
