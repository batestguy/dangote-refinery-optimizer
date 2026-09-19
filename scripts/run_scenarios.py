"""Phase 5 scenario study — 10k-draw Monte Carlo + committed risk artifacts.

Runs the historical-block-bootstrap Monte Carlo (``optimization/scenarios.py``)
on the production slate/prices/costs and writes:

* ``data/derived/scenarios_phase5.json`` — base/vaR/CVaR metrics, switch
  frequencies, tornado decomposition, provenance (committed)
* ``docs/assets/margin_fan.png`` — margin distribution fan (5/25/50/75/95 pct
  of re-optimized margins across Brent-shock buckets)
* ``docs/assets/tornado_margin.png`` — product-price tornado on the base LP

Timing: 10k LP re-solves on the reused Phase 4 skeleton — well under a minute.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dangote_opt.config import CONFIG
from dangote_opt.data.assays import frame_to_records
from dangote_opt.data.costs import build_crude_costs, load_brent_reference
from dangote_opt.data.prices import product_prices, usgc_prices_frame
from dangote_opt.features.quality import CRUDE_QUALITIES
from dangote_opt.optimization.baselines import build_lp_problem, solve_lp
from dangote_opt.optimization.scenarios import (
    N_ITERATIONS,
    bootstrap_price_draws,
    historical_changes,
    run_scenarios,
)

SLATE = "data/derived/slate_phase1.parquet"
OUT_JSON = Path("data/derived/scenarios_phase5.json")
ASSETS = Path("docs/assets")
SEED = 20260919


def _cached_frame(series_key: str) -> pd.DataFrame:
    """Sidecar-located offline cache read (shared client helper)."""
    from dangote_opt.data.acquire import load_cached_series

    return load_cached_series(series_key)


def load_inputs() -> tuple:
    """Production wiring: slate, costs, prices, LP skeleton, history."""
    records = frame_to_records(pd.read_parquet(SLATE))
    curves = [np.array(r.tbp_curve, dtype=float) for r in records]
    try:
        brent_ref, brent_frame = load_brent_reference()
    except FileNotFoundError:
        sidecar = json.loads(Path("data/derived/costs_phase2.json").read_text(encoding="utf-8"))
        brent_ref = float(sidecar["brent_reference_usd_bbl"])
        brent_frame = None  # filled from the offline cache below
    costs_map = build_crude_costs([r.crude_id for r in records], brent_ref)
    costs = np.array([costs_map[r.crude_id] for r in records])
    try:
        pf = usgc_prices_frame("")  # cache-first
    except Exception:  # noqa: BLE001 — offline fallback via sidecar lookup
        pf = _cached_frame("us_product_prices")
    prices_map = product_prices(pf)
    prices = np.array([prices_map[p] for p in CONFIG.products])
    quals = [CRUDE_QUALITIES[r.crude_id] for r in records]
    problem = build_lp_problem(curves, costs, quals, CONFIG)

    # History for the bootstrap (needs the frames, not just the anchors).
    if brent_frame is None:
        brent_frame = _brent_frame()
    return records, curves, brent_ref, costs, prices, pf, problem


def fan_chart(draws: np.ndarray, margins: np.ndarray, path: Path) -> None:
    """Margin quantile fan across Brent-shock buckets."""
    order = np.argsort(draws[:, 0])
    b = draws[order, 0]
    m = margins[order]
    buckets = np.array_split(np.arange(len(m)), 20)
    centers = [b[ix].mean() for ix in buckets]
    q05 = [np.percentile(m[ix], 5) for ix in buckets]
    q25 = [np.percentile(m[ix], 25) for ix in buckets]
    q50 = [np.percentile(m[ix], 50) for ix in buckets]
    q75 = [np.percentile(m[ix], 75) for ix in buckets]
    q95 = [np.percentile(m[ix], 95) for ix in buckets]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.array(centers) * 100  # % Brent change
    ax.fill_between(x, q05, q95, alpha=0.25, color="#1f77b4", label="5–95 pct")
    ax.fill_between(x, q25, q75, alpha=0.45, color="#1f77b4", label="25–75 pct")
    ax.plot(x, q50, color="#1f77b4", lw=2, label="median")
    ax.axhline(0, color="#d62728", lw=1, ls="--", label="break-even")
    ax.set_xlabel("12-month Brent change (%)")
    ax.set_ylabel("Re-optimized margin ($/bbl)")
    ax.set_title(f"Margin fan — {N_ITERATIONS:,} correlated price scenarios (block bootstrap)")
    ax.legend(frameon=False, loc="lower left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def tornado_chart(tornado: dict[str, tuple[float, float]], base: float, path: Path) -> None:
    """Standard tornado: bars spanning margin at −10% → +10% per product."""
    items = sorted(tornado.items(), key=lambda kv: abs(kv[1][1] - kv[1][0]), reverse=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    y = np.arange(len(items))
    for k, (_name, (lo, hi)) in enumerate(items):
        ax.barh(k, hi - lo, left=lo, height=0.55, color="#1f77b4", alpha=0.8)
        ax.text(lo - 0.15, k, f"${lo:.1f}", va="center", ha="right", fontsize=8)
        ax.text(hi + 0.15, k, f"${hi:.1f}", va="center", ha="left", fontsize=8)
    ax.axvline(base, color="#d62728", lw=1.4, ls="--", label=f"base ${base:.2f}")
    ax.set_yticks(y, [n.title() for n, _ in items])
    ax.set_xlabel("Re-optimized margin ($/bbl)")
    ax.set_title("Tornado — ±10% product-price shocks, optimal response")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    records, curves, brent_ref, costs, prices, pf, problem = load_inputs()
    names = [r.name for r in records]
    base = solve_lp(problem, prices)

    changes = historical_changes(_brent_frame(), pf)
    draws = bootstrap_price_draws(changes, N_ITERATIONS, SEED)

    t0 = time.perf_counter()
    result = run_scenarios(problem, prices, base.ratios, base.severity, draws, brent_ref)
    elapsed = time.perf_counter() - t0

    ASSETS.mkdir(parents=True, exist_ok=True)
    fan_chart(draws, result.optimal_margins, ASSETS / "margin_fan.png")
    tornado_chart(result.tornado, result.base_margin, ASSETS / "tornado_margin.png")

    summary = {
        "n_iterations": result.n_iterations,
        "seed": SEED,
        "base_margin": result.base_margin,
        "mean_margin": float(result.optimal_margins.mean()),
        "margin_std": float(result.optimal_margins.std()),
        "var_pct": result.var_pct,
        "cvar_pct": result.cvar_pct,
        "fixed_blend_mean": float(result.fixed_blend_margins.mean()),
        "fixed_var_pct": result.fixed_var_pct,
        "fixed_cvar_pct": result.fixed_cvar_pct,
        "reopt_value_mean": float((result.optimal_margins - result.fixed_blend_margins).mean()),
        "probability_of_loss": result.probability_of_loss,
        "avg_severity": result.avg_severity,
        "switch_share": {n: float(s) for n, s in zip(names, result.switch_share, strict=True)},
        "tornado": {k: list(v) for k, v in result.tornado.items()},
        "brent_cost_sensitivity": -1.0,
        "runtime_s": elapsed,
        "provenance": result.provenance,
        "base_blend": {n: float(v) for n, v in zip(names, base.ratios, strict=True)},
        "base_severity": base.severity,
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"{N_ITERATIONS:,} scenarios in {elapsed:.1f}s")
    print(
        f"base ${result.base_margin:.2f} | mean ${result.optimal_margins.mean():.2f} "
        f"± {result.optimal_margins.std():.2f}"
    )
    print(
        f"VaR(5%) ${result.var_pct:.2f} | CVaR(5%) ${result.cvar_pct:.2f} "
        f"| P(loss) {result.probability_of_loss:.1%}"
    )
    print(
        f"fixed blend: mean ${result.fixed_blend_margins.mean():.2f} "
        f"| re-opt value ${summary['reopt_value_mean']:.2f}/bbl"
    )
    print(f"switch share: {summary['switch_share']}")
    print(f"figures → {ASSETS}/, summary → {OUT_JSON}")


def _brent_frame() -> pd.DataFrame:
    """Brent cache frame (bootstrap history), offline-safe."""
    return _cached_frame("brent_spot")


if __name__ == "__main__":
    main()
