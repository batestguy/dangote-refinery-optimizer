"""Parsers for published crude-assay PDFs — Phase 1 (docs/data_provenance.md row 3).

Two vendor formats are supported (both verified 2026-09-19 against real sheets):

* **TotalEnergies crude data sheets** (trading.totalenergies.com): one page with
  whole-crude properties (°API, Sulphur wt-%, density) and a TBP DISTILLATION
  table of (°C, wt-%, vol-%) rows — two table halves share one text line, and
  left-column property labels can share a line with right-column TBP rows.
* **ExxonMobil Crude Summary Reports** (corporate.exxonmobil.com): page 1 has
  whole-crude properties (``API Gravity``, ``Total Sulfur (% wt)``); page 2 has a
  cumulative *volume-%* grid at 10 °C intervals (rows = start temperatures, 10
  values each; axis-label rows are exact ``+10`` sequences and are filtered out).

Yield basis is recorded per record (``vol_pct`` or ``wt_pct``) — the Phase 2
bridge consumes vol-% TBP curves and must never mix bases silently.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from dangote_opt.data.assays import AssayRecord

_NUM = r"(\d+(?:\.\d+)?)"


def _parse_float(text: str) -> float:
    return float(text.replace(",", ""))


def _require_api_sulfur(
    api: float | None, sulfur: float | None, source: str
) -> tuple[float, float]:
    if api is None or sulfur is None:
        raise ValueError(f"{source}: could not extract API gravity and sulfur from PDF")
    return api, sulfur


# --------------------------------------------------------------------------- #
# TotalEnergies format
# --------------------------------------------------------------------------- #
def parse_totalenergies_sheet(
    pdf_path: str | Path, *, crude_id: str, name: str, url: str
) -> AssayRecord:
    """Parse a TotalEnergies crude data sheet (single page, two TBP half-tables)."""
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    api = sulfur = None
    for ln in lines:
        m = re.search(rf"°API\s+{_NUM}", ln)
        if m and api is None:
            api = _parse_float(m.group(1))
        m = re.search(rf"Sulphur,?\s*wt%\s+{_NUM}", ln)
        if m and sulfur is None:
            sulfur = _parse_float(m.group(1))
    api, sulfur = _require_api_sulfur(api, sulfur, str(pdf_path))

    assay_date = ""
    if m := re.search(r"Assay Date\s+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{2})", text):
        assay_date = m.group(1)

    # TBP rows: '<T> <wt%> <vol%>', two half-tables sharing one text line, and
    # left-column properties can share a line with right-column TBP rows
    # (e.g. "°API 34.9 080 7.4 9.8 460 84.1 86.2" holds TWO TBP rows).
    # Guards against false matches from cut-property rows ("NAPHTHA 80-150 13.0…")
    # and decimal fragments ("0.163 60 41.0"): temperature must be a multiple of
    # 10 in [80, 580], not preceded by '.'/'-'/digit, and vol% >= wt%.
    # The curve is stored on the VOL% column for every crude (uniform basis for
    # the Phase 2 bridge; TE publishes both, XOM publishes vol% only).
    row_re = re.compile(rf"(?<![.\-\d])(0?[1-5]\d0|0[89]0)\s+{_NUM}\s+{_NUM}(?=\s|$)")
    seen: dict[float, float] = {}
    for ln in lines:
        for m in row_re.finditer(ln):
            temp = float(m.group(1))
            wt_pct = _parse_float(m.group(2))
            vol_pct = _parse_float(m.group(3))
            if 80 <= temp <= 580 and 0 <= wt_pct <= vol_pct + 1e-9 <= 100:
                seen.setdefault(temp, vol_pct)
    curve = tuple(sorted(seen.items()))
    if len(curve) < 2:
        raise ValueError(f"{pdf_path}: no TBP rows parsed")

    return AssayRecord(
        crude_id=crude_id,
        name=name,
        api=api,
        sulfur_pct=sulfur,
        tbp_curve=curve,
        source="TotalEnergies crude oil data sheet",
        source_url=url,
        pulled="2026-09-19",
        notes=(
            f"assay date {assay_date}; TBP yield basis: vol%"
            if assay_date
            else "TBP yield basis: vol%"
        ),
    )


# --------------------------------------------------------------------------- #
# ExxonMobil format
# --------------------------------------------------------------------------- #
def parse_exxonmobil_report(
    pdf_path: str | Path, *, crude_id: str, name: str, url: str
) -> AssayRecord:
    """Parse an ExxonMobil Crude Summary Report (properties p1, TBP grid p2)."""
    with pdfplumber.open(pdf_path) as pdf:
        page1 = pdf.pages[0].extract_text() or ""
        page2 = pdf.pages[1].extract_text() if len(pdf.pages) > 1 else ""

    api_m = re.search(rf"API Gravity\s+{_NUM}", page1)
    s_m = re.search(rf"Total Sulfur \(% wt\)\s+{_NUM}", page1)
    api = _parse_float(api_m.group(1)) if api_m else None
    sulfur = _parse_float(s_m.group(1)) if s_m else None
    api, sulfur = _require_api_sulfur(api, sulfur, str(pdf_path))

    ref = ""
    if m := re.search(r"Reference:\s*(\S+)", page1):
        ref = m.group(1)
    date = ""
    if m := re.search(r"Assay Date:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", page1):
        date = m.group(1)

    # Cumulative volume-% grid: row starts with a round temperature, then values.
    # Axis-label rows (chart ticks) are exact +10 sequences — exclude them.
    curve: list[tuple[float, float]] = []
    for ln in (page2 or "").splitlines():
        cells = ln.split()
        if not cells or not cells[0].isdigit():
            continue
        temp = float(cells[0])
        vals = [_parse_float(c) for c in cells[1:] if re.fullmatch(r"\d+(?:\.\d+)?", c)]
        if len(vals) < 2:
            continue
        if vals == [vals[0] + 10 * i for i in range(len(vals))]:  # axis labels
            continue
        for i, v in enumerate(vals):
            curve.append((temp + 10 * (i + 1), v))
    curve = sorted(curve)
    if len(curve) < 2:
        raise ValueError(f"{pdf_path}: no TBP grid rows parsed")

    return AssayRecord(
        crude_id=crude_id,
        name=name,
        api=api,
        sulfur_pct=sulfur,
        tbp_curve=tuple(curve),
        source="ExxonMobil Crude Summary Report",
        source_url=url,
        pulled="2026-09-19",
        notes=(
            f"reference {ref}; assay date {date}; TBP yield basis: vol% (10 °C cumulative grid)"
            if ref or date
            else "TBP yield basis: vol%"
        ),
    )


# --------------------------------------------------------------------------- #
# The verified Phase 1 slate
# --------------------------------------------------------------------------- #
RAW_DIR = Path("data/raw/assays")

SLATE_SPECS: list[dict[str, str]] = [
    {
        "crude_id": "bonny_light",
        "name": "Bonny Light",
        "file": "BONNY-LIGHT.pdf",
        "url": "https://trading.totalenergies.com/wp-content/uploads/2025/11/BONNY-LIGHT.pdf",
        "parser": "totalenergies",
    },
    {
        "crude_id": "forcados",
        "name": "Forcados",
        "file": "FORCADOS.pdf",
        "url": "https://trading.totalenergies.com/wp-content/uploads/2025/11/FORCADOS.pdf",
        "parser": "totalenergies",
    },
    {
        "crude_id": "qua_iboe",
        "name": "Qua Iboe",
        "file": "QUA-IBOE.pdf",
        "url": "https://corporate.exxonmobil.com/-/media/global/files/crude-oils/pdf/2024/qua_iboe.pdf",
        "parser": "exxonmobil",
    },
    {
        "crude_id": "alaska_north_slope",
        "name": "Alaska North Slope",
        "file": "ALASKA-NORTH-SLOPE.pdf",
        "url": "https://corporate.exxonmobil.com/-/media/global/files/crude-oils/pdf/alaska_north_slope.pdf",
        "parser": "exxonmobil",
    },
    {
        "crude_id": "thunder_horse",
        "name": "Thunder Horse",
        "file": "THUNDER-HORSE.pdf",
        "url": "https://corporate.exxonmobil.com/-/media/global/files/crude-oils/pdf/thunder_horse.pdf",
        "parser": "exxonmobil",
    },
]


def build_slate(raw_dir: str | Path = RAW_DIR) -> list[AssayRecord]:
    """Parse all five verified sheets into validated AssayRecords.

    Raises:
        FileNotFoundError: a PDF is missing (download scripts/eia-style first).
        ValueError | AssayValidationError: any sheet fails to parse/validate.
    """
    records: list[AssayRecord] = []
    for spec in SLATE_SPECS:
        path = Path(raw_dir) / spec["file"]
        if not path.exists():
            raise FileNotFoundError(f"{path} missing — download it from {spec['url']}")
        if spec["parser"] == "totalenergies":
            records.append(
                parse_totalenergies_sheet(
                    path, crude_id=spec["crude_id"], name=spec["name"], url=spec["url"]
                )
            )
        else:
            records.append(
                parse_exxonmobil_report(
                    path, crude_id=spec["crude_id"], name=spec["name"], url=spec["url"]
                )
            )
    return records
