"""Train the Phase 3 ETR surrogate and write artifacts.

Deterministic end-to-end (seeded sampling + seeded forest): re-running this
script reproduces ``models/etr_surrogate.pkl`` bit-for-bit in distribution —
which is why the pkl itself is gitignored while ``models/model_card.md`` is
committed (heavy binary vs. deliverable document).

Usage:  uv run python scripts/train_surrogate.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dangote_opt.models.dataset import DatasetSpec, build_dataset  # noqa: E402
from dangote_opt.models.train_surrogate import (  # noqa: E402
    save_surrogate,
    train_etr_surrogate,
    write_model_card,
)

PKL_LIMIT_MB = 50  # spec §3.7 hosting guard


def main() -> int:
    spec = DatasetSpec(n_samples=4000)
    X, Y = build_dataset(spec)
    print(f"dataset: {len(X)} rows (seed {spec.seed})")

    bundle = train_etr_surrogate(X, Y, spec=spec)
    save_surrogate(bundle, "models/etr_surrogate.pkl")
    write_model_card(bundle, "models/model_card.md")

    size_mb = os.path.getsize("models/etr_surrogate.pkl") / 1e6
    print(f"pkl: {size_mb:.1f} MB (guard < {PKL_LIMIT_MB} MB)")
    if size_mb >= PKL_LIMIT_MB:
        raise SystemExit(f"pkl exceeds the {PKL_LIMIT_MB} MB hosting guard — shrink the forest")

    print(
        "random 5-fold  :",
        {t: round(m["r2"], 4) for t, m in bundle["cv_random"].items()},
    )
    print(
        "leave-crude-out:",
        {t: round(m["r2"], 4) for t, m in bundle["cv_leave_crude_out"].items()},
    )
    min_r2 = min(m["r2"] for m in bundle["cv_random"].values())
    gate = (
        "PASS (>0.90 impressive)"
        if min_r2 > 0.90
        else ("PASS (>0.80 viable)" if min_r2 > 0.80 else "FAIL")
    )
    print(f"gate: min random-5-fold R2 = {min_r2:.4f} → {gate}")
    print("model card written to models/model_card.md (committed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
