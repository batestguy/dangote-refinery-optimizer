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

    return mo, np


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
    from dangote_opt.features.bridge import (
        blend_yields_batch,
        light_naphtha_fractions,
        tbp_cut_fractions,
        yields_from_assay,
    )
    from dangote_opt.features.quality import (
        CRUDE_QUALITIES,
        BatchQualityModel,
        blend_pool_qualities,
    )
    from dangote_opt.optimization.objective import RefineryObjective, simplex_repair

    # REAL slate — parsed published assays (docs/data_provenance.md row 3).
    df = pd.read_parquet("data/derived/slate_phase1.parquet")
    records = frame_to_records(df)
    CRUDES = [r.name for r in records]
    CURVES = [np.array(r.tbp_curve, dtype=float) for r in records]
    CRUDE_CUTS = np.array([tbp_cut_fractions(c) for c in CURVES])
    LIGHT_NAP = light_naphtha_fractions(CURVES)

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
    crude_quals = [CRUDE_QUALITIES[r.crude_id] for r in records]

    def quality_model(ratios, severity):
        return blend_pool_qualities(ratios, CURVES, crude_quals, severity)

    def bridge_yields(ratios, severity):
        """Blend yield = crude-weighted mean of per-crude bridge yields."""
        ys = np.array(
            [
                yields_from_assay(r.api, r.sulfur_pct, c, severity)
                for r, c in zip(records, CURVES, strict=True)
            ]
        )
        return ratios @ ys

    def batch_bridge_yields(X, s):
        """Exact-linear batch path — same mass balance, one vectorized pass."""
        return blend_yields_batch(
            np.array([r.api for r in records]),
            np.array([r.sulfur_pct for r in records]),
            per_crude_cuts=CRUDE_CUTS,
            light_naphtha=LIGHT_NAP,
            ratios_batch=X,
            severities=s,
        )

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
            CRUDE_CUTS,
            severity_range=tuple(bundle["card"]["severity_training_range"]),
        )
        BATCH_YIELDS = YIELD_MODEL.batch
        SURROGATE_INFO = bundle["card"]
    else:
        YIELD_MODEL = bridge_yields
        BATCH_YIELDS = batch_bridge_yields
        SURROGATE_INFO = None

    objective = RefineryObjective(
        crude_apis=np.array([r.api for r in records]),
        crude_sulfurs=np.array([r.sulfur_pct for r in records]),
        crude_costs=COSTS,
        product_prices=PRICE_VEC,
        yield_model=YIELD_MODEL,
        quality_model=quality_model,
        batch_yields=BATCH_YIELDS,
        batch_quality=BatchQualityModel.from_slate(CURVES, crude_quals),
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
    mo,
    np,
    objective,
    run,
):
    # marimo renders only the last *top-level* expression of a cell — an output
    # nested inside `if run.value:` is silently dropped. mo.stop() short-circuits
    # with a message instead, and the result mo.md() is the final statement.
    mo.stop(
        not run.value,
        mo.md("Set the baseline severity, then hit **Run** to optimize the blend."),
    )

    # Phase 4 driver: vectorized DE over the exact batch paths + the mandatory
    # 3-way baseline table (equal-weight / random search / LP — spec §3.4).
    from dangote_opt.optimization.de_driver import DE_BUDGET_S
    from dangote_opt.optimization.de_driver import optimize_blend as run_opt

    result = run_opt(objective)
    x, sev, margin_de = result.best_x, result.best_severity, result.best_margin
    x_eq = np.full(CONFIG.n_crudes, 1 / CONFIG.n_crudes)
    margin_eq = objective.margin(x_eq, baseline_severity.value)
    uplift = (margin_de - margin_eq) / abs(margin_eq) if margin_eq else float("nan")

    rows = "\n".join(f"| {name} | {xi:.1%} |" for name, xi in zip(CRUDES, x, strict=True))
    violations = result.violations
    status = "✅ feasible" if not violations else f"⚠️ {violations}"

    def _b(key):
        b = result.baselines.get(key)
        return f"${b.margin:,.2f}" if b else "—"

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
    budget_note = (
        f"{result.runtime_s:.1f}s run — inside the {DE_BUDGET_S:.0f}s budget"
        if not result.over_budget
        else f"⚠️ {result.runtime_s:.1f}s — OVER the {DE_BUDGET_S:.0f}s budget"
    )
    mo.md(
        f"""
        ### Optimal crude diet (bridge yields · Brent costs · USGC prices · quality specs)
        | Crude | Blend share |
        |---|---|
        {rows}

        **FCC severity (DE):** {sev:.2f} · **Blend margin (DE):** ${margin_de:,.2f}/bbl
        · **Uplift vs equal-weight** (severity {baseline_severity.value:.2f}):
        {uplift:+.1%}
        · **Constraints:** {status}

        | Baseline (spec §3.4) | Margin ($/bbl) |
        |---|---|
        | DE optimum | {margin_de:,.2f} |
        | LP optimum (honest bar) | {_b("lp")} |
        | Random search (10k feasible draws) | {_b("random_search")} |
        | Equal-weight | {_b("equal_weight")} |

        {model_note} · **Runtime:** {budget_note}.
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
