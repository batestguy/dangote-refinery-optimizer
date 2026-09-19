"""Build the Phase 1 five-crude slate — parse published assay PDFs → parquet.

Run after the vendor PDFs are downloaded into data/raw/assays/ (see
docs/data_provenance.md row 3 for URLs). Writes:

* ``data/derived/slate_phase1.parquet`` — the committed slate artifact
  (data/derived/ is tracked; data/raw/ is not).
* ``data/derived/slate_phase1.json`` — provenance sidecar (source URLs, pull
  date, parser per crude, yield bases).

The PDFs themselves stay in the gitignored data/raw/ (vendor documents, not
redistributed); the parsed numbers with full source URLs are what we commit.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dangote_opt.data.assay_parsers import SLATE_SPECS, build_slate  # noqa: E402
from dangote_opt.data.assays import records_to_frame, validate_slate  # noqa: E402

DERIVED_DIR = Path("data/derived")


def main() -> int:
    records = build_slate()
    validate_slate(records, n_expected=5)

    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = DERIVED_DIR / "slate_phase1.parquet"
    records_to_frame(records).to_parquet(parquet_path, index=False)

    sidecar = {
        "artifact": str(parquet_path),
        "generated": datetime.now(UTC).date().isoformat(),
        "n_crudes": len(records),
        "sources": [
            {
                "crude_id": r.crude_id,
                "source": r.source,
                "url": r.source_url,
                "pulled": r.pulled,
                "notes": r.notes,
            }
            for r in records
        ],
        "pdfs": [s["file"] for s in SLATE_SPECS],
    }
    (DERIVED_DIR / "slate_phase1.json").write_text(json.dumps(sidecar, indent=2))
    print(f"wrote {parquet_path} ({len(records)} crudes) + sidecar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
