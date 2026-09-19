"""Phase 4 tests — DE driver, baseline contract, and batch-path exactness.

The batch paths are the load-bearing performance piece (30–60 s app budget,
spec §3.7), so their equivalence to the scalar paths is pinned to solver
precision here, on the real committed slate.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dangote_opt.config import CONFIG
from dangote_opt.data.assays import frame_to_records
from dangote_opt.data.costs import build_crude_costs
from dangote_opt.features.bridge import (
    blend_yields_batch,
    light_naphtha_fractions,
    tbp_cut_fractions,
    yields_from_assay,
)
from dangote_opt.features.quality import CRUDE_QUALITIES, BatchQualityModel, blend_pool_qualities
from dangote_opt.optimization.baselines import (
    equal_weight_baseline,
    lp_baseline,
    random_search_baseline,
)
from dangote_opt.optimization.de_driver import optimize_blend
from dangote_opt.optimization.objective import RefineryObjective

SLATE = "data/derived/slate_phase1.parquet"


@pytest.fixture(scope="module")
def wired():
    """Production-shaped objective on the real slate (scalar + batch paths)."""
    records = frame_to_records(pd.read_parquet(SLATE))
    curves = [np.array(r.tbp_curve, dtype=float) for r in records]
    cuts = np.array([tbp_cut_fractions(c) for c in curves])
    light = light_naphtha_fractions(curves)
    apis = np.array([r.api for r in records])
    sulfurs = np.array([r.sulfur_pct for r in records])
    quals = [CRUDE_QUALITIES[r.crude_id] for r in records]

    sidecar = json.loads(Path("data/derived/costs_phase2.json").read_text(encoding="utf-8"))
    costs_map = build_crude_costs(
        [r.crude_id for r in records], float(sidecar["brent_reference_usd_bbl"])
    )
    costs = np.array([costs_map[r.crude_id] for r in records])
    prices_sidecar = json.loads(Path("data/derived/prices_phase2.json").read_text(encoding="utf-8"))
    prices = np.array([prices_sidecar["prices_usd_bbl"][p] for p in CONFIG.products])

    def batch_yields(X, s):
        return blend_yields_batch(
            apis, sulfurs, per_crude_cuts=cuts, light_naphtha=light, ratios_batch=X, severities=s
        )

    def scalar_yields(ratios, severity):
        per = np.array(
            [
                yields_from_assay(r.api, r.sulfur_pct, c, severity)
                for r, c in zip(records, curves, strict=True)
            ]
        )
        return ratios @ per

    def quality_model(ratios, severity):
        return blend_pool_qualities(ratios, curves, quals, severity)

    objective = RefineryObjective(
        apis,
        sulfurs,
        costs,
        prices,
        yield_model=scalar_yields,
        quality_model=quality_model,
        batch_yields=batch_yields,
        batch_quality=BatchQualityModel.from_slate(curves, quals),
    )
    return {
        "objective": objective,
        "curves": curves,
        "costs": costs,
        "prices": prices,
        "qualities": quals,
        "records": records,
        "cuts": cuts,
        "light": light,
        "apis": apis,
        "sulfurs": sulfurs,
        "quals": quals,
    }


def test_bridge_batch_matches_scalar(wired):
    """blend_yields_batch ≡ per-blend pooling of yields_from_assay (machine eps)."""
    rng = np.random.default_rng(11)
    X = rng.dirichlet(np.full(CONFIG.n_crudes, 0.55), size=32)
    s = rng.uniform(0.0, 1.0, size=32)
    Y = blend_yields_batch(
        wired["apis"],
        wired["sulfurs"],
        per_crude_cuts=wired["cuts"],
        light_naphtha=wired["light"],
        ratios_batch=X,
        severities=s,
    )
    for i in range(len(X)):
        per = np.array(
            [
                yields_from_assay(r.api, r.sulfur_pct, c, float(s[i]))
                for r, c in zip(wired["records"], wired["curves"], strict=True)
            ]
        )
        assert np.abs(X[i] @ per - Y[i]).max() < 1e-12


def test_quality_batch_matches_scalar(wired):
    """BatchQualityModel row-wise ≡ blend_pool_qualities (solver precision)."""
    rng = np.random.default_rng(12)
    X = rng.dirichlet(np.full(CONFIG.n_crudes, 0.55), size=24)
    s = rng.uniform(0.0, 1.0, size=24)
    bq = BatchQualityModel.from_slate(wired["curves"], wired["quals"])
    Q = bq.qualities(X, s)
    for i in range(len(X)):
        scalar = blend_pool_qualities(X[i], wired["curves"], wired["quals"], float(s[i]))
        for key in scalar:
            assert scalar[key] == pytest.approx(float(Q[key][i]), abs=1e-9)


def test_batch_call_matches_scalar_call(wired):
    """objective.batch_call ≡ __call__ row-wise, both axis conventions."""
    obj = wired["objective"]
    rng = np.random.default_rng(13)
    pop = rng.uniform(0.0, 1.0, size=(12, CONFIG.n_crudes + 1))
    scalar = np.array([obj(row) for row in pop])
    assert np.abs(obj.batch_call(pop) - scalar).max() < 1e-6
    assert np.abs(obj.batch_call(pop.T.copy()) - scalar).max() < 1e-6


def test_driver_runs_inside_budget_and_finds_lp_optimum(wired):
    """DE ≈ LP on bridge-exact physics; runtime inside the 30–60 s budget."""
    obj = wired["objective"]
    res = optimize_blend(
        obj, lp_inputs=(wired["curves"], wired["costs"], wired["prices"], wired["quals"])
    )
    assert res.feasible
    assert res.runtime_s < 60.0
    assert not res.over_budget
    assert res.de_success
    assert len(res.convergence) > 0
    # The honest bar (problem statement §4): DE matches the exact LP within
    # tolerance on the bridge's own physics (margin is linear in the vars).
    lp = res.baselines["lp"]
    assert res.best_margin == pytest.approx(lp.margin, abs=5e-3)
    # Baseline ordering on this slate.
    assert lp.margin >= res.baselines["random_search"].margin - 1e-6
    assert res.baselines["random_search"].margin >= res.baselines["equal_weight"].margin


def test_random_search_returns_feasible_best(wired):
    obj = wired["objective"]
    res = random_search_baseline(obj, n_draws=2_000, seed=7)
    assert obj.constraints_violated(res.ratios, res.severity) == []
    assert res.margin > 0  # positive-margin feasible blend found on this slate


def test_equal_weight_baseline(wired):
    res = equal_weight_baseline(wired["objective"], severity=0.5)
    assert np.allclose(res.ratios, np.full(CONFIG.n_crudes, 1 / CONFIG.n_crudes))
    assert res.severity == 0.5


def test_lp_baseline_hard_quality_constraints(wired):
    """The LP optimum satisfies the quality specs *exactly* (hard constraints)."""
    res = lp_baseline(wired["curves"], wired["costs"], wired["prices"], wired["quals"])
    obj = wired["objective"]
    assert obj.constraints_violated(res.ratios, res.severity) == []
    assert res.margin > 0
