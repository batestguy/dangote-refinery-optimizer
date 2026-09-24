"""Phase 4 sensitivity study — ≥100 DE seeds (spec §3.4) + committed figures.

Builds the production objective exactly as the app does (real slate, bridge +
surrogate batch paths, quality specs, Brent-anchored costs, USGC prices), runs
``optimize_blend`` across 100 seeds, and writes:

* ``docs/assets/convergence.png``    — DE convergence curve (seed 42) with
  equal-weight and LP reference lines
* ``docs/assets/seed_sensitivity.png`` — margin histogram across the sweep
* ``data/derived/sensitivity_phase4.json`` — per-seed results + summary stats
  (sidecar carries provenance: seeds, model wiring, runtime)

The DE optimum's blend is seed-independent up to tolerance in practice; the
spread quantifies how sharply the margin is determined.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from dangote_opt.config import CONFIG
from dangote_opt.data.assays import frame_to_records
from dangote_opt.data.costs import build_crude_costs, load_brent_reference
from dangote_opt.data.prices import product_prices, usgc_prices_frame
from dangote_opt.features.bridge import (
    blend_yields_batch,
    light_naphtha_fractions,
    tbp_cut_fractions,
    yields_from_assay,
)
from dangote_opt.features.quality import CRUDE_QUALITIES, BatchQualityModel, blend_pool_qualities
from dangote_opt.models.train_surrogate import SurrogateYieldModel, load_surrogate
from dangote_opt.optimization.de_driver import optimize_blend
from dangote_opt.optimization.objective import RefineryObjective
from dangote_opt.viz.convergence import plot_convergence, plot_seed_sensitivity

SLATE = "data/derived/slate_phase1.parquet"
N_SEEDS = 100
OUT_JSON = Path("data/derived/sensitivity_phase4.json")
ASSETS = Path("docs/assets")


def build_objective() -> tuple[RefineryObjective, list, np.ndarray, np.ndarray, list]:
    """Wire the production objective (same construction as app/app.py)."""
    records = frame_to_records(pd.read_parquet(SLATE))
    curves = [np.array(r.tbp_curve, dtype=float) for r in records]
    cuts = np.array([tbp_cut_fractions(c) for c in curves])
    light = light_naphtha_fractions(curves)
    apis = np.array([r.api for r in records])
    sulfurs = np.array([r.sulfur_pct for r in records])
    quals = [CRUDE_QUALITIES[r.crude_id] for r in records]

    try:
        brent_ref, _ = load_brent_reference()
    except FileNotFoundError:
        sidecar = json.loads(Path("data/derived/costs_phase2.json").read_text(encoding="utf-8"))
        brent_ref = float(sidecar["brent_reference_usd_bbl"])
    costs_map = build_crude_costs([r.crude_id for r in records], brent_ref)
    costs = np.array([costs_map[r.crude_id] for r in records])

    try:
        prices = product_prices(usgc_prices_frame(""))  # cache-first; no key needed
    except Exception:  # noqa: BLE001 — offline fallback to committed artifact
        sidecar = json.loads(Path("data/derived/prices_phase2.json").read_text(encoding="utf-8"))
        prices = np.array([sidecar["prices_usd_bbl"][p] for p in CONFIG.products])

    def batch_yields(X, s):  # noqa: ANN001, ANN202
        return blend_yields_batch(
            apis, sulfurs, per_crude_cuts=cuts, light_naphtha=light, ratios_batch=X, severities=s
        )

    def scalar_yields(ratios, severity):  # noqa: ANN001, ANN202
        per = np.array(
            [
                yields_from_assay(r.api, r.sulfur_pct, c, severity)
                for r, c in zip(records, curves, strict=True)
            ]
        )
        return ratios @ per

    yield_model = scalar_yields
    pkl = Path("models/etr_surrogate.pkl")
    if pkl.exists():
        bundle = load_surrogate(pkl)
        surrogate = SurrogateYieldModel(
            bundle["model"],
            apis,
            sulfurs,
            cuts,
            severity_range=tuple(bundle["card"]["severity_training_range"]),
        )
        yield_model = surrogate

    def quality_model(ratios, severity):  # noqa: ANN001, ANN202
        return blend_pool_qualities(ratios, curves, quals, severity)

    objective = RefineryObjective(
        apis,
        sulfurs,
        costs,
        prices,
        yield_model=yield_model,
        quality_model=quality_model,
        batch_yields=batch_yields if not pkl.exists() else surrogate.batch,
        batch_quality=BatchQualityModel.from_slate(curves, quals),
    )
    return objective, curves, costs, prices, quals


def main() -> None:
    objective, curves, costs, prices, quals = build_objective()
    records = frame_to_records(pd.read_parquet(SLATE))
    names = [r.name for r in records]

    seeds = list(range(CONFIG.de_seed_baseline, CONFIG.de_seed_baseline + N_SEEDS))
    rows: list[dict] = []
    t0 = time.perf_counter()
    for seed in seeds:
        res = optimize_blend(
            objective,
            seed=seed,
            with_baselines=(seed == seeds[0]),
            lp_inputs=(curves, costs, prices, quals) if seed == seeds[0] else None,
        )
        rows.append(
            {
                "seed": seed,
                "margin": res.best_margin,
                "severity": res.best_severity,
                "runtime_s": res.runtime_s,
                "n_evaluations": res.n_evaluations,
                "iterations": len(res.convergence),
                "feasible": res.feasible,
                **{f"x_{i}": float(v) for i, v in enumerate(res.best_x)},
            }
        )
    sweep_s = time.perf_counter() - t0

    margins = np.array([r["margin"] for r in rows])
    first = optimize_blend(objective, seed=seeds[0], lp_inputs=(curves, costs, prices, quals))
    best = rows[0]

    ASSETS.mkdir(parents=True, exist_ok=True)
    plot_convergence(
        first.convergence,
        lp_margin=first.baselines["lp"].margin if "lp" in first.baselines else None,
        equal_weight_margin=first.baselines["equal_weight"].margin,
    ).savefig(ASSETS / "convergence.png", dpi=150)
    plot_seed_sensitivity(margins).savefig(ASSETS / "seed_sensitivity.png", dpi=150)

    summary = {
        "n_seeds": N_SEEDS,
        "margin_mean": float(margins.mean()),
        "margin_std": float(margins.std()),
        "margin_min": float(margins.min()),
        "margin_max": float(margins.max()),
        "sweep_runtime_s": sweep_s,
        "baseline_seed": best["seed"],
        "baselines": {
            k: {"margin": b.margin, "severity": b.severity} for k, b in first.baselines.items()
        },
        "uplift_vs_equal_weight": float(
            (first.best_margin - first.baselines["equal_weight"].margin)
            / abs(first.baselines["equal_weight"].margin)
        ),
        "wiring": {
            "yield_model": "surrogate" if Path("models/etr_surrogate.pkl").exists() else "bridge",
            "quality": "BatchQualityModel (exact mirror)",
            "seeds": seeds,
        },
        "per_seed": rows,
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"sweep: {N_SEEDS} seeds in {sweep_s:.1f}s ({sweep_s / N_SEEDS:.2f}s/run)")
    print(
        f"margin: mean ${margins.mean():.2f} ± {margins.std():.2f} "
        f"[{margins.min():.2f}, {margins.max():.2f}]"
    )
    for k, b in first.baselines.items():
        print(f"  {k:13s} ${b.margin:6.2f}")
    print(f"uplift vs equal-weight: {summary['uplift_vs_equal_weight']:+.1%}")
    print(f"figures → {ASSETS}/, summary → {OUT_JSON}")
    print(
        "blend (seed 42):",
        {n: round(float(v), 3) for n, v in zip(names, first.best_x, strict=True)},
    )


if __name__ == "__main__":
    main()
