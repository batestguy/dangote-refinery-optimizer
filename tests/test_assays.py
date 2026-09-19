"""Assay record validation tests — provenance doc Phase 1 exit criteria."""

from __future__ import annotations

import pandas as pd
import pytest

from dangote_opt.data.assays import (
    AssayRecord,
    AssayValidationError,
    frame_to_records,
    records_to_frame,
    validate_slate,
)


def make_record(**overrides) -> AssayRecord:
    base = dict(
        crude_id="bonny_light",
        name="Bonny Light",
        api=33.4,
        sulfur_pct=0.16,
        tbp_curve=((20.0, 0.0), (180.0, 30.0), (360.0, 62.0), (540.0, 86.0)),
        source="ExxonMobil crude oils",
        source_url="https://example.com/assay",
        pulled="2026-09-19",
    )
    base.update(overrides)
    return AssayRecord(**base)


def test_valid_record_passes():
    rec = make_record()
    rec.validate()  # no raise


def test_api_out_of_range_rejected():
    with pytest.raises(AssayValidationError, match="API"):
        make_record(api=52.0)


def test_sulfur_out_of_range_rejected():
    with pytest.raises(AssayValidationError, match="sulfur"):
        make_record(sulfur_pct=6.0)


def test_tbp_needs_two_points():
    with pytest.raises(AssayValidationError, match=">= 2"):
        make_record(tbp_curve=((20.0, 0.0),))


def test_tbp_temps_must_increase():
    with pytest.raises(AssayValidationError, match="strictly increase"):
        make_record(tbp_curve=((20.0, 0.0), (180.0, 30.0), (180.0, 40.0)))


def test_tbp_yields_bounded():
    with pytest.raises(AssayValidationError, match="yields"):
        make_record(tbp_curve=((20.0, 0.0), (180.0, 130.0)))


def test_provenance_required():
    with pytest.raises(AssayValidationError, match="provenance"):
        make_record(source="")


def test_imputation_flag_roundtrip():
    rec = make_record(imputed=("tbp_curve: tail imputed from VGO correlation",))
    row = rec.to_frame_row()
    assert any("tbp_curve" in flag for flag in row["imputed"])
    back = AssayRecord.from_frame_row(row)
    assert back.imputed == rec.imputed
    assert back.tbp_curve == rec.tbp_curve


def test_frame_roundtrip_preserves_records():
    records = [
        make_record(),
        make_record(crude_id="arab_light", name="Arab Light", api=33.3, sulfur_pct=2.9),
    ]
    df = records_to_frame(records)
    assert isinstance(df, pd.DataFrame) and len(df) == 2
    rebuilt = frame_to_records(df)
    assert rebuilt == records


def test_slate_rejects_duplicates():
    with pytest.raises(AssayValidationError, match="duplicate"):
        validate_slate([make_record(), make_record()])


def test_slate_rejects_wrong_size():
    with pytest.raises(AssayValidationError, match="exactly 5"):
        validate_slate([make_record()])
