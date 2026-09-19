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
    from dotenv import dotenv_values

    from dangote_opt.config import CONFIG
    from dangote_opt.data.assays import frame_to_records
    from dangote_opt.data.costs import build_crude_costs, load_brent_reference
    from dangote_opt.data.prices import product_prices, usgc_prices_frame
    from dangote_opt.features.bridge import tbp_cut_fractions, yields_from_assay
    from dangote_opt.features.quality import CRUDE_QUALITIES, blend_pool_qualities
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

    # REAL product prices — EIA USGC spot 12-mo averages (gasoline/diesel/jet);
    # petrochem stays on the disclosed CONFIG placeholder. Falls back to the
    # committed artifact when no key/cache is available.
    try:
        price_frame = usgc_prices_frame(dotenv_values(".env").get("EIA_API_KEY", "").strip() or "")
        PRICES = product_prices(price_frame)
    except Exception:  # noqa: BLE001 — offline fallback to the committed artifact
        price_sidecar = json.loads(
            Path("data/derived/prices_phase2.json").read_text(encoding="utf-8")
        )
        PRICES = price_sidecar["prices_usd_bbl"]
    PRICE_VEC = np.array([PRICES[p] for p in CONFIG.products])

    # REAL quality model — pool qualities from the bridge's component streams
    # (features/quality.py); RON/RVP/freeze/cetane specs join the penalty block.
    curves = [np.array(r.tbp_curve, dtype=float) for r in records]
    crude_quals = [CRUDE_QUALITIES[r.crude_id] for r in records]

    def quality_model(ratios, severity):
        return blend_pool_qualities(ratios, curves, crude_quals, severity)

    def bridge_yields(ratios, severity):
        """Blend yield = crude-weighted mean of per-crude bridge yields."""
        ys = np.array(
            [
                yields_from_assay(r.api, r.sulfur_pct, np.array(r.tbp_curve), severity)
                for r in records
            ]
        )
        return ratios @ ys

    # Phase 3 surrogate when trained (scripts/train_surrogate.py) — it learns
    # the bridge and reproduces it to <0.1% inside the envelope (model card).
    # The bridge remains the source of truth and the fallback. The quality
    # model stays bridge-exact (cheap; surrogate ≈ bridge anyway).
    surrogate_pkl = Path("models/etr_surrogate.pkl")
    if surrogate_pkl.exists():
        from dangote_opt.models.train_surrogate import SurrogateYieldModel, load_surrogate

        bundle = load_surrogate(surrogate_pkl)
        YIELD_MODEL = SurrogateYieldModel(
            bundle["model"],
            np.array([r.api for r in records]),
            np.array([r.sulfur_pct for r in records]),
            np.array([tbp_cut_fractions(np.array(r.tbp_curve, dtype=float)) for r in records]),
            severity_range=tuple(bundle["card"]["severity_training_range"]),
        )
        SURROGATE_INFO = bundle["card"]
    else:
        YIELD_MODEL = bridge_yields
        SURROGATE_INFO = None

    objective = RefineryObjective(
        crude_apis=np.array([r.api for r in records]),
        crude_sulfurs=np.array([r.sulfur_pct for r in records]),
        crude_costs=COSTS,
        product_prices=PRICE_VEC,
        yield_model=YIELD_MODEL,
        quality_model=quality_model,
    )
    return (
        CONFIG,
        CRUDES,
        COSTS,
        PRICES,
        SURROGATE_INFO,
        objective,
        quality_model,
        simplex_repair,
    )


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
    SURROGATE_INFO,
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
    if SURROGATE_INFO is not None:
        min_r2 = min(m["r2"] for m in SURROGATE_INFO["cv_random_5fold"].values())
        model_note = (
            f"**Yield model:** ETR surrogate (Phase 3) — labels are the cited "
            f"Stage-1 bridge; random 5-fold R² ≥ {min_r2:.3f}, leave-crude-out "
            f"reported in `models/model_card.md`."
        )
    else:
        model_note = (
            "**Yield model:** Stage-1 TBP bridge directly "
            "(train the surrogate with `scripts/train_surrogate.py`)."
        )
    mo.md(
        f"""
        ### Optimal crude diet (bridge yields · Brent costs · USGC prices · quality specs)
        | Crude | Blend share |
        |---|---|
        {rows}

        **FCC severity (DE):** {sev:.2f} · **Blend margin (DE):** ${margin_de:,.2f}/bbl
        · **Equal-weight baseline** (severity {baseline_severity.value:.2f}):
        ${margin_eq:,.2f}/bbl
        · **Uplift:** {uplift:+.1%}
        · **Constraints:** {status}

        {model_note}
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
        per-grade differentials (row 9, refresh: OPEC MOMR); gasoline/diesel/jet
        prices are real EIA USGC spot averages (row 2) — the **petrochem pool
        price is a disclosed PLACEHOLDER** (no citable spot series exists).
        Yields come from the Stage-1 TBP bridge and quality specs (RON/RVP/freeze/
        cetane) from `features/quality.py` — component values PUBLISHED where the
        sheets provide them, **ASSUMED** otherwise (`docs/methodology.md` §3c).
        Methodology demo on public data — not Dangote's actual operations (spec §7).
        """
    )
    return


if __name__ == "__main__":
    app.run()
