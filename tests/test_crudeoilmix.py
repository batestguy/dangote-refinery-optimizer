"""CrudeOilMix mapper + streaming tests — fully offline (fake datasets module)."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

from dangote_opt.data import crudeoilmix as com


def mixrow(oilid: str, inner: dict[str, Any], n_components: int = 1) -> dict[str, Any]:
    return {
        "oilid": oilid,
        "n_components": n_components,
        "is_blend": n_components > 1,
        "mix_json": json.dumps(inner),
    }


class FakeHFDataset:
    """Mimics the streaming iterable surface used by stream_whole_crudes."""

    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


@pytest.fixture
def fake_datasets(monkeypatch: pytest.MonkeyPatch):
    """Patch the lazy `from datasets import load_dataset` inside the module."""
    rows = [
        mixrow(
            "A1",
            {
                "whole_crude_api": 33.4,
                "whole_crude_sulfur_wt_pct": 0.16,
                "whole_crude_tbp_curve": [[20, 0], [180, 30], [360, 60], [540, 85]],
            },
        ),
        mixrow("A2", {"api": 31.7, "sulfur": 1.30}),  # shorter suffix variants
        mixrow("B1", {"whole_crude_api": 40.0}, n_components=3),  # blend -> filtered out
        mixrow("BAD", {"nonsense_key": 1}),  # maps to nothing -> reject on strict use
        {"no_mix_json": True},  # structurally invalid -> reject
    ]
    holders: dict[str, Any] = {}

    def fake_load_dataset(repo_id: str, split: str = "train", streaming: bool = False):
        holders["repo_id"] = repo_id
        holders["streaming"] = streaming
        return FakeHFDataset(rows)

    import datasets  # dependency of the mapper's lazy import

    monkeypatch.setattr(datasets, "load_dataset", fake_load_dataset)
    return holders, rows


def test_map_mix_row_maps_by_suffix(fake_datasets):
    mapped = com.map_mix_row(mixrow("X", {"whole_crude_api": 33.4, "sulfur_wt_pct": 0.2}))
    assert mapped.properties["api"] == 33.4
    assert mapped.properties["sulfur_pct"] == 0.2
    assert mapped.unmapped_keys == ()


def test_map_mix_row_unknown_keys_collected(fake_datasets):
    mapped = com.map_mix_row(mixrow("X", {"api": 30.0, "mystery": 7}))
    assert mapped.properties == {"api": 30.0}
    assert mapped.unmapped_keys == ("mystery",)


def test_map_mix_row_strict_raises_on_unknown(fake_datasets):
    with pytest.raises(ValueError, match="unmapped"):
        com.map_mix_row(mixrow("X", {"api": 30.0, "mystery": 7}), strict=True)


def test_map_mix_row_accepts_dict_mix_json(fake_datasets):
    mapped = com.map_mix_row({"oilid": "X", "mix_json": {"api": 30.0}})
    assert mapped.properties["api"] == 30.0


def test_map_mix_row_rejects_bad_json(fake_datasets):
    with pytest.raises(ValueError, match="not valid JSON"):
        com.map_mix_row({"oilid": "X", "mix_json": "{not json"})


def test_map_mix_row_requires_keys(fake_datasets):
    with pytest.raises(KeyError):
        com.map_mix_row({"oilid": "X"})


def test_map_streamed_rows_splits_good_and_rejects(fake_datasets):
    rows = [
        mixrow("OK", {"api": 30.0}),
        {"no_mix_json": True},
        mixrow("BADJSON", None),  # type: ignore[list-item] — handled as reject
    ]
    rows[2]["mix_json"] = "%%%notjson%%%"
    good, rejects = com.map_streamed_rows(rows)
    assert list(good["oilid"]) == ["OK"]
    assert list(rejects["oilid"]) == ["<missing>", "BADJSON"]  # stream order
    assert set(rejects.columns) == {"oilid", "reason"}


def test_stream_whole_crudes_filters_blends_and_limits(fake_datasets):
    holders, rows = fake_datasets
    collected = com.stream_whole_crudes(n=2)
    assert holders["repo_id"] == com.HF_DATASET_ID
    assert holders["streaming"] is True
    ids = [r["oilid"] for r in collected]
    assert ids == ["A1", "A2"]  # blend B1 filtered; order preserved
    assert all(int(r["n_components"]) <= 1 for r in collected)


def test_stream_whole_crudes_no_limit(fake_datasets):
    # Malformed row (no oilid/mix_json) is skipped; BAD (valid structure,
    # unmappable content) still streams — rejects are map_streamed_rows' job.
    collected = com.stream_whole_crudes()
    assert [r["oilid"] for r in collected] == ["A1", "A2", "BAD"]


def test_mapped_rows_feed_assay_validation():
    """Mapped properties must be AssayRecord-compatible shapes (tuple TBP)."""
    mapped = com.map_mix_row(
        mixrow(
            "A1",
            {
                "whole_crude_api": 33.4,
                "whole_crude_tbp_curve": [[20, 0], [180, 30], [360, 60], [540, 85]],
            },
        )
    )
    tbp = mapped.properties["tbp_curve"]
    assert isinstance(tbp, list) and len(tbp[0]) == 2
    temps = [pt[0] for pt in tbp]
    assert temps == sorted(temps)


def test_load_mix_json_parquet_validates_columns(tmp_path):
    df = pd.DataFrame(
        {"oilid": ["A"], "n_components": [1], "is_blend": [False], "mix_json": ['{"api": 30}']}
    )
    p = tmp_path / "mix.parquet"
    df.to_parquet(p, index=False)
    out = com.load_mix_json_parquet(str(p))
    assert list(out["oilid"]) == ["A"]
    missing = tmp_path / "nope.parquet"
    with pytest.raises(FileNotFoundError):
        com.load_mix_json_parquet(str(missing))
