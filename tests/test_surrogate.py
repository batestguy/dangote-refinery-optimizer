"""Phase 3 surrogate tests — dataset generator, dual-CV training, YieldModel
wrapper, persistence, and objective integration (all offline, fast configs)."""

from __future__ import annotations

import pickle

import numpy as np
import pandas as pd
import pytest

from dangote_opt.models.dataset import (
    FEATURE_COLUMNS,
    LABEL_COLUMNS,
    DatasetSpec,
    build_dataset,
    load_slate,
)
from dangote_opt.models.train_surrogate import SurrogateYieldModel, train_etr_surrogate

SLATE_PARQUET = "data/derived/slate_phase1.parquet"


@pytest.fixture(scope="module")
def small_bundle():
    """Fast deterministic bundle for CI: real forest config, small dataset."""
    spec = DatasetSpec(n_samples=400, seed=7)
    X, Y = build_dataset(spec)
    return train_etr_surrogate(X, Y, spec=spec, seed=7)


# --- dataset -----------------------------------------------------------------


def test_dataset_is_deterministic():
    X1, Y1 = build_dataset(DatasetSpec(n_samples=60, seed=11))
    X2, Y2 = build_dataset(DatasetSpec(n_samples=60, seed=11))
    pd.testing.assert_frame_equal(X1, X2)
    pd.testing.assert_frame_equal(Y1, Y2)


def test_dataset_rows_and_columns():
    X, Y = build_dataset(DatasetSpec(n_samples=50, seed=3))
    assert len(X) == len(Y) == 50
    assert list(X.columns) == list(FEATURE_COLUMNS)
    assert list(Y.columns) == list(LABEL_COLUMNS)


def test_dataset_features_cover_design_space():
    X, _ = build_dataset(DatasetSpec(n_samples=300, seed=5))
    assert X["severity"].between(0, 1).all()
    assert X["api_blend"].between(30, 38).all()  # slate's actual API span
    # cut fractions are blend-weighted → sum to ~1 per row
    cut_sum = sum(X[c] for c in FEATURE_COLUMNS[3:])
    assert np.allclose(cut_sum, 1.0, atol=1e-9)


def test_dataset_labels_are_bridge_exact():
    """Every label row must equal the blend-weighted bridge yields exactly."""
    from dangote_opt.features.bridge import yields_from_assay

    spec = DatasetSpec(n_samples=40, seed=13)
    slate = load_slate()
    X, Y = build_dataset(spec, slate)
    rng = np.random.default_rng(0)
    for i in rng.integers(0, len(X), size=5):
        row = X.iloc[i]
        x = np.linalg.lstsq(
            slate.cut_fractions.T,
            row[list(FEATURE_COLUMNS[3:])].to_numpy(dtype=float),
            rcond=None,
        )[0]
        x = np.clip(x, 0, None)
        x = x / x.sum()
        expected = sum(
            x[j]
            * yields_from_assay(slate.apis[j], slate.sulfurs[j], slate.curves[j], row["severity"])
            for j in range(len(x))
        )
        got = Y.iloc[i][list(LABEL_COLUMNS)].to_numpy(dtype=float)
        assert np.allclose(got, expected, atol=5e-3)


# --- training / dual CV -------------------------------------------------------


def test_dual_cv_reports_both_protocols(small_bundle):
    card = small_bundle["card"]
    assert set(card["cv_random_5fold"]) == set(LABEL_COLUMNS)
    assert set(card["cv_leave_crude_out"]) == set(LABEL_COLUMNS)


def test_surrogate_beats_viable_gate_on_headline(small_bundle):
    """Tiny forest/dataset still interpolates the smooth bridge well."""
    min_r2 = min(m["r2"] for m in small_bundle["cv_random"].values())
    assert min_r2 > 0.90  # spec §5 'impressive' bar


def test_surrogate_respects_severity_direction(small_bundle):
    """Inside the envelope, higher severity must mean more gasoline (the
    bridge's dominant monotone response must survive training)."""
    slate = load_slate()
    sur = SurrogateYieldModel(
        small_bundle["model"],
        slate.apis,
        slate.sulfurs,
        slate.cut_fractions,
        severity_range=(0.0, 1.0),
    )
    x = np.full(5, 0.2)
    lo = sur(x, 0.1)
    hi = sur(x, 0.9)
    assert hi[0] > lo[0]  # gasoline up
    assert hi[3] < lo[3]  # petrochem down


def test_surrogate_yields_bounded_and_sum_plausible(small_bundle):
    slate = load_slate()
    sur = SurrogateYieldModel(small_bundle["model"], slate.apis, slate.sulfurs, slate.cut_fractions)
    rng = np.random.default_rng(1)
    for _ in range(10):
        x = rng.dirichlet(np.ones(5))
        y = sur(x, float(rng.random()))
        assert (y >= 0).all()
        assert (y <= 1).all()
        assert 0.9 <= y.sum() <= 1.05  # bridge sums ≈ 0.997


def test_surrogate_clips_out_of_envelope_severity(small_bundle):
    slate = load_slate()
    sur = SurrogateYieldModel(
        small_bundle["model"],
        slate.apis,
        slate.sulfurs,
        slate.cut_fractions,
        severity_range=(0.05, 0.95),
    )
    inside = sur(np.full(5, 0.2), 0.95)
    outside = sur(np.full(5, 0.2), 1.7)
    assert np.allclose(inside, outside)  # clipped to 0.95


# --- persistence ---------------------------------------------------------------


def test_persistence_roundtrip(tmp_path, small_bundle):
    from dangote_opt.models.train_surrogate import save_surrogate

    p = tmp_path / "sur.pkl"
    save_surrogate(small_bundle, p)
    with open(p, "rb") as f:
        loaded = pickle.load(f)
    slate = load_slate()
    x = np.full(5, 0.2)
    a = SurrogateYieldModel(small_bundle["model"], slate.apis, slate.sulfurs, slate.cut_fractions)(
        x, 0.5
    )
    b = SurrogateYieldModel(loaded["model"], slate.apis, slate.sulfurs, slate.cut_fractions)(x, 0.5)
    assert np.allclose(a, b)


# --- objective integration -----------------------------------------------------


def test_objective_accepts_surrogate_yield_model(small_bundle):
    from dangote_opt.optimization.objective import RefineryObjective

    slate = load_slate()
    sur = SurrogateYieldModel(small_bundle["model"], slate.apis, slate.sulfurs, slate.cut_fractions)
    obj = RefineryObjective(
        crude_apis=slate.apis,
        crude_sulfurs=slate.sulfurs,
        crude_costs=np.full(5, 70.0),
        product_prices=np.array([95.0, 100.0, 90.0, 70.0]),
        yield_model=sur,
    )
    x = np.r_[np.full(5, 0.2), 0.5]
    assert np.isfinite(obj(x))


def test_model_card_written(small_bundle, tmp_path):
    from dangote_opt.models.train_surrogate import write_model_card

    p = tmp_path / "model_card.md"
    write_model_card(small_bundle, p)
    text = p.read_text(encoding="utf-8")
    assert "Random 5-fold" in text
    assert "Leave-crude-out" in text
    assert "Honesty analysis" in text  # jet-R2≈0 explanation present
