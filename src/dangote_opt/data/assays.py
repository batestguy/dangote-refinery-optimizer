"""Crude assay records + validation — Phase 1 (docs/data_provenance.md row 3).

The 5-crude slate's assays come from public vendor/agency sources (ExxonMobil,
TotalEnergies, Equinor, NUPRC). Every record is validated against the provenance
doc's Phase 1 exit criteria *before* it can enter the bridge (Phase 2):

* API gravity in [10, 50]
* sulfur in [0, 5] wt-%
* TBP curve: >=2 points, temperatures strictly increasing, yield 0–100 %
  (the curve must rise; the doc's "TBP monotonic 0–100 %" rule)

Each record keeps its provenance (source name + URL + pull date) and any
documented imputation, so the "is this real?" interviewer question always has
an answer. Unit sanity lives *here*, not downstream — the bridge can trust
``AssayRecord.validate()``-cleared data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

API_RANGE = (10.0, 50.0)
SULFUR_RANGE = (0.0, 5.0)  # wt-%
YIELD_RANGE = (0.0, 100.0)  # TBP mass/vol-% recovered


class AssayValidationError(ValueError):
    """An assay record violates the provenance doc's data-quality rules."""


@dataclass(frozen=True)
class AssayRecord:
    """One crude assay. ``api``/``sulfur_pct`` are floats; ``tbp_curve`` rows are
    (temperature_c, pct_recovered) pairs with temperatures strictly increasing."""

    crude_id: str
    name: str
    api: float
    sulfur_pct: float
    tbp_curve: tuple[tuple[float, float], ...]
    source: str
    source_url: str
    pulled: str
    notes: str = ""
    imputed: tuple[str, ...] = field(default=tuple())

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Raise AssayValidationError on any provenance-doc rule violation."""
        if not self.crude_id or not self.name:
            raise AssayValidationError("crude_id and name must be non-empty")
        if not (API_RANGE[0] <= self.api <= API_RANGE[1]):
            raise AssayValidationError(f"{self.crude_id}: API {self.api} outside {API_RANGE}")
        if not (SULFUR_RANGE[0] <= self.sulfur_pct <= SULFUR_RANGE[1]):
            raise AssayValidationError(
                f"{self.crude_id}: sulfur {self.sulfur_pct} wt-% outside {SULFUR_RANGE}"
            )
        if len(self.tbp_curve) < 2:
            raise AssayValidationError(f"{self.crude_id}: TBP curve needs >= 2 points")
        temps = [t for t, _ in self.tbp_curve]
        pcts = [p for _, p in self.tbp_curve]
        if any(b <= a for a, b in zip(temps[:-1], temps[1:], strict=True)):
            raise AssayValidationError(
                f"{self.crude_id}: TBP temperatures must strictly increase, got {temps}"
            )
        if any(not (YIELD_RANGE[0] <= p <= YIELD_RANGE[1]) for p in pcts):
            raise AssayValidationError(
                f"{self.crude_id}: TBP yields must be in {YIELD_RANGE} %, got {pcts}"
            )
        # A cumulative distillation curve cannot decrease with temperature
        # (0.1 %-point tolerance for rounding in published tables).
        pairs = list(zip(self.tbp_curve, self.tbp_curve[1:], strict=False))
        dips = [(t1, y1, y2) for (t1, y1), (t2, y2) in pairs if y2 < y1 - 0.1]
        if dips:
            raise AssayValidationError(
                f"{self.crude_id}: TBP yield decreases with temperature at {dips[:3]}"
            )
        if not self.source or not self.source_url or not self.pulled:
            raise AssayValidationError(
                f"{self.crude_id}: provenance (source, source_url, pulled) is required"
            )

    def to_frame_row(self) -> dict[str, object]:
        """One row for the slate parquet (TBP kept as a nested list column)."""
        return {
            "crude_id": self.crude_id,
            "name": self.name,
            "api": self.api,
            "sulfur_pct": self.sulfur_pct,
            "tbp_curve": [list(pt) for pt in self.tbp_curve],
            "source": self.source,
            "source_url": self.source_url,
            "pulled": self.pulled,
            "notes": self.notes,
            "imputed": list(self.imputed),
        }

    @classmethod
    def from_frame_row(cls, row: dict[str, object]) -> AssayRecord:
        """Round-trip from to_frame_row output (parquet read)."""
        return cls(
            crude_id=str(row["crude_id"]),
            name=str(row["name"]),
            api=float(row["api"]),  # type: ignore[arg-type]
            sulfur_pct=float(row["sulfur_pct"]),  # type: ignore[arg-type]
            tbp_curve=tuple((float(t), float(p)) for t, p in row["tbp_curve"]),  # type: ignore[arg-type]
            source=str(row["source"]),
            source_url=str(row["source_url"]),
            pulled=str(row["pulled"]),
            notes=str(row.get("notes", "")),
            imputed=tuple(row.get("imputed", tuple())),  # type: ignore[arg-type]
        )


def records_to_frame(records: list[AssayRecord]) -> pd.DataFrame:
    """Slate frame: one validated record per row, ready for parquet."""
    return pd.DataFrame([r.to_frame_row() for r in records])


def frame_to_records(df: pd.DataFrame) -> list[AssayRecord]:
    """Rebuild validated records from a slate frame (re-runs validate())."""
    return [AssayRecord.from_frame_row(row) for row in df.to_dict("records")]


def validate_slate(records: list[AssayRecord], n_expected: int = 5) -> None:
    """Slate-level rules: unique ids, exact size (scope guard, CONFIG.n_crudes).

    Raises:
        AssayValidationError: on duplicates, wrong size, or any invalid record.
    """
    ids = [r.crude_id for r in records]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise AssayValidationError(f"duplicate crude_id values: {dupes}")
    if len(records) != n_expected:
        raise AssayValidationError(
            f"slate must have exactly {n_expected} crudes, got {len(records)}"
        )
    for r in records:
        r.validate()
