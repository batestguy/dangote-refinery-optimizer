"""Dangote Refinery Blend Optimizer — marimo app (POC).

The file that deploys to HuggingFace Spaces unchanged (Phase 6, spec §3.7).
Runs locally with:  uv run marimo run app/app.py

Yields come from the Stage-1 TBP bridge (real published assays) and costs from
the EIA Brent anchor + documented differentials; product prices remain
placeholder until the EIA USGC series is wired in. Methodology-demo outputs,
not real Dangote data.
"""

import marimo

__generated_with = "0.12.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    from scipy.optimize import differential_evolution

    return differential_evolution, mo, np


@app.cell
def _(np):
    import json
    from pathlib import Path

    import pandas as pd

    from dangote_opt.config import CONFIG
    from dangote_opt.data.assays import frame_to_records
    from dangote_opt.data.costs import build_crude_costs, load_brent_reference
    from dangote_opt.features.bridge import yields_from_assay
    from dangote_opt.optimization.objective import RefineryObjective, simplex_repair

    # REAL slate — parsed published assays (docs/data_provenance.md row 3).
    df = pd.read_parquet("data/derived/slate_phase1.parquet")
    records = frame_to_records(df)
    CRUDES = [r.name for r in records]

    # REAL cost anchor — EIA Brent trailing-12m average + documented per-grade
    # differentials (docs/data_provenance.md row 9; differentials are ASSUMED).
    # Falls back to the committed artifact's Brent reference when no live key.
    try:
        brent_ref, _ = load_brent_reference()
    except FileNotFoundError:
        cost_sidecar = json.loads(
            Path("data/derived/costs_phase2.json").read_text(encoding="utf-8")
        )
        brent_ref = float(cost_sidecar["brent_reference_usd_bbl"])
    costs_map = build_crude_costs([r.crude_id for r in records], brent_ref)
    COSTS = np.array([costs_map[r.crude_id] for r in records])

    def bridge_yields(ratios, severity):
        """Blend yield = crude-weighted mean of per-crude bridge yields."""
        ys = np.array(
            [
                yields_from_assay(r.api, r.sulfur_pct, np.array(r.tbp_curve), severity)
                for r in records
            ]
        )
        return ratios @ ys

    objective = RefineryObjective(
        crude_apis=np.array([r.api for r in records]),
        crude_sulfurs=np.array([r.sulfur_pct for r in records]),
        crude_costs=COSTS,
        product_prices=np.array([CONFIG.default_prices[p] for p in CONFIG.products]),
        yield_model=bridge_yields,
    )
    return CONFIG, CRUDES, COSTS, objective, simplex_repair


@app.cell
def _(mo):
    # DE optimizes severity itself (spec §3.6); this slider sets the *baseline*
    # severity for the equal-weight comparison (spec §3.4: "at default severity").
    baseline_severity = mo.ui.slider(
        0.0, 1.0, value=0.5, step=0.01, label="Baseline FCC severity (equal-weight comparison)"
    )
    run = mo.ui.run_button(label="⚡ Run deep optimization")
    mo.vstack([baseline_severity, run])
    return baseline_severity, run


@app.cell
def _(
    CONFIG,
    CRUDES,
    baseline_severity,
    differential_evolution,
    mo,
    np,
    objective,
    run,
    simplex_repair,
):
    # marimo renders only the last *top-level* expression of a cell — an output
    # nested inside `if run.value:` is silently dropped. mo.stop() short-circuits
    # with a message instead, and the result mo.md() is the final statement.
    mo.stop(
        not run.value,
        mo.md("Set the baseline severity, then hit **Run** to optimize the blend."),
    )

    bounds = [(0.0, 1.0)] * CONFIG.n_crudes + [CONFIG.severity_bounds]
    result = differential_evolution(
        objective,
        bounds,
        maxiter=CONFIG.de_maxiter,
        popsize=CONFIG.de_popsize,
        seed=CONFIG.de_seed_baseline,
        polish=False,
        tol=1e-3,
    )
    x = simplex_repair(result.x[: CONFIG.n_crudes])
    sev = float(np.clip(result.x[-1], *CONFIG.severity_bounds))
    # Report the *unpenalized* margin; feasibility is shown separately below.
    margin_de = objective.margin(x, sev)
    x_eq = np.full(CONFIG.n_crudes, 1 / CONFIG.n_crudes)
    margin_eq = objective.margin(x_eq, baseline_severity.value)
    uplift = (margin_de - margin_eq) / abs(margin_eq) if margin_eq else float("nan")

    rows = "\n".join(f"| {name} | {xi:.1%} |" for name, xi in zip(CRUDES, x, strict=True))
    violations = objective.constraints_violated(x, sev)
    status = "✅ feasible" if not violations else f"⚠️ {violations}"
    mo.md(
        f"""
        ### Optimal crude diet (Stage-1 TBP bridge yields + real Brent-anchored costs)
        | Crude | Blend share |
        |---|---|
        {rows}

        **FCC severity (DE):** {sev:.2f} · **Blend margin (DE):** ${margin_de:,.2f}/bbl
        · **Equal-weight baseline** (severity {baseline_severity.value:.2f}):
        ${margin_eq:,.2f}/bbl
        · **Uplift:** {uplift:+.1%}
        · **Constraints:** {status}
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        **Transparency:** crude assays are real published data (TotalEnergies /
        ExxonMobil sheets — `docs/data_provenance.md` row 3); delivered costs are
        anchored to the real EIA Brent spot average plus documented **ASSUMED**
        per-grade differentials (row 9) — refresh path: OPEC MOMR. Product prices
        remain **placeholder** until the EIA USGC series is wired in; yields come
        from the Stage-1 TBP cut-point bridge (`docs/methodology.md`). Methodology
        demo on public data — not Dangote's actual operations (spec §7).
        """
    )
    return


if __name__ == "__main__":
    app.run()
