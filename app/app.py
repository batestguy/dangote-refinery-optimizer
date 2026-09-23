"""Dangote Refinery Blend Optimizer — marimo dashboard (Phase 6).

The file that deploys to HuggingFace Spaces unchanged (spec §3.7).
Runs locally with:  uv run marimo run app/app.py

Cold-start discipline (HF Spaces sleep ~48 h): the page renders its whole
static story from committed artifacts first — KPI strip, market ticker,
optimal-diet and regime-switch charts, scenario-risk table, fan/tornado
figures — and only the deep re-opt waits for a button click. Live feeds
(FX/WTI) degrade to timestamped stale/snapshot values; nothing on the page
ever shows a number without its provenance badge or as-of date.

Methodology demo on public data — not real Dangote operations (spec §7).
"""

import marimo

__generated_with = "0.24.2"
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

    # Precomputed Phase 4/5 artifacts — the cold-start-safe story layer.
    SC = json.loads(Path("data/derived/scenarios_phase5.json").read_text(encoding="utf-8"))
    SENS = json.loads(Path("data/derived/sensitivity_phase4.json").read_text(encoding="utf-8"))

    return (
        CONFIG,
        CRUDES,
        COSTS,
        CRUDE_CUTS,
        CURVES,
        PRICES,
        PRICE_VEC,
        SC,
        SENS,
        SURROGATE_INFO,
        crude_quals,
        objective,
        simplex_repair,
    )


@app.cell
def _(CONFIG, mo):
    mo.md(
        f"""
        # Dangote Refinery Blend Optimizer

        **Crude-blend + FCC-severity optimization at refinery scale** —
        {CONFIG.n_crudes} real published crude assays, a cited TBP cut-point
        bridge to {len(CONFIG.products)} product pools, quality specs with real
        teeth (RON / RVP / freeze / cetane), and a differential-evolution
        optimizer benchmarked against an exact LP.

        *Methodology demo on free/open data — provenance for every number in
        `docs/methodology.md`; not Dangote's actual operations (spec §7).*
        """
    )
    return


@app.cell
def _(SC, SENS, SURROGATE_INFO, mo):
    # Headline KPI strip — every value precomputed in committed artifacts, so
    # this renders instantly on a sleeping Space (no model load, no network).
    if SURROGATE_INFO is not None:
        _min_r2 = min(m["r2"] for m in SURROGATE_INFO["cv_random_5fold"].values())
        model_kpi = f"{_min_r2:.3f}"
        model_footnote = (
            "Surrogate loaded (`models/etr_surrogate.pkl`, deterministic) — "
            "dual-CV details incl. the leave-crude-out honesty finding: "
            "`models/model_card.md`."
        )
    else:
        model_kpi = "bridge¹"
        model_footnote = (
            "¹ Surrogate not trained in this environment "
            "(`scripts/train_surrogate.py`, ~5 s, deterministic) — the app then "
            "runs the exact bridge, same optimum."
        )

    margin_kpi = f"${SC['base_margin']:.2f}/bbl"
    uplift_kpi = f"{SENS['uplift_vs_equal_weight']:+.1%}"
    reopt_kpi = f"+${SC['reopt_value_mean']:.2f}/bbl"
    risk_kpi = f"${SC['var_pct']:.2f} · ${SC['cvar_pct']:.2f} · {SC['probability_of_loss']:.1%}"

    mo.md(
        f"""
        | Headline (precomputed, deterministic) | Value |
        |---|---|
        | **Blend margin** — LP optimum, base prices | **{margin_kpi}** |
        | **Uplift vs equal-weight blend** (100-seed sweep) | **{uplift_kpi}** |
        | **Value of re-optimization** under price shocks | **{reopt_kpi}** |
        | **VaR(5%)** · CVaR(5%) · P(loss) — 10k scenarios | {risk_kpi} |
        | Surrogate 5-fold R² (min across products) | {model_kpi} |

        {model_footnote}
        """
    )
    return


@app.cell
def _(mo):
    # Live ticker (Phase 6, provenance rows 2 + 8): NGN/USD FX (open.er-api.com,
    # keyless, 1 h disk cache) + WTI spot (EIA daily, YCUOK). Live attempt first;
    # graceful fallback to the committed snapshot (cold-start-safe on HF Spaces,
    # where there is no EIA key and data/raw/ is not shipped). Every value is
    # rendered with its as-of date — never a timestamp-less number.
    import json as _tjson
    from pathlib import Path as _tpath

    from dotenv import dotenv_values as _dotenv_values

    from dangote_opt.data.ticker import fetch_ngn_usd_rate as _fetch_fx
    from dangote_opt.data.ticker import fetch_wti_spot as _fetch_wti

    _snapshot = _tjson.loads(_tpath("data/derived/ticker_latest.json").read_text(encoding="utf-8"))

    def _mark(live_q, snap_q):
        """(quote, badge) — live quote if reachable, else the staged snapshot."""
        if live_q is not None:
            return live_q, "🟢 live" if not live_q.stale else "🟡 stale cache"
        q = type("Q", (), {})()  # render the snapshot with the same shape
        q.value, q.as_of, q.source = (
            snap_q["value"],
            snap_q["as_of"],
            snap_q["source"],
        )
        return q, "🔵 snapshot"

    _fx_live = _wti_live = None
    try:
        _fx_live = _fetch_fx()
    except Exception:  # noqa: BLE001 — ticker must never break the dashboard
        pass
    try:
        _wti_live = _fetch_wti(_dotenv_values(".env").get("EIA_API_KEY", "").strip())
    except Exception:  # noqa: BLE001
        pass

    _fx, _fx_badge = _mark(_fx_live, _snapshot["quotes"]["ngn_usd"])
    _wti, _wti_badge = _mark(_wti_live, _snapshot["quotes"]["wti_spot"])

    mo.md(
        f"""
        ## Market ticker

        | Feed | Value | As of | Status |
        |---|---|---|---|
        | NGN/USD FX | {_fx.value:,.2f} ₦/$ | {_fx.as_of} | {_fx_badge} |
        | WTI spot | ${_wti.value:,.2f}/bbl | {_wti.as_of} | {_wti_badge} |

        *Display-only context — neither feed enters the optimization (USD
        single-period price-taker, spec §7). FX: open.er-api.com free tier,
        cached 1 h (provenance row 8); WTI: EIA daily spot (Cushing). 🔵
        snapshot = committed `data/derived/ticker_latest.json`, regenerated
        {_snapshot["generated_utc"][:10]} via `scripts/refresh_ticker_snapshot.py`.*
        """
    )
    return


@app.cell
def _(SC, mo):
    # Blend story as charts — both from the committed Phase 5 artifact.
    import plotly.express as _px

    _diet = sorted(SC["base_blend"].items(), key=lambda kv: -kv[1])

    def _bar(pairs, title):
        fig = _px.bar(
            x=[k for k, _ in pairs],
            y=[v * 100 for _, v in pairs],
            text=[f"{v * 100:.1f}%" for _, v in pairs],
        )
        fig.update_layout(
            title=title,
            template="plotly_white",
            yaxis_title="share (%)",
            margin=dict(t=48, r=16, b=16),
            height=340,
        )
        fig.update_yaxes(range=[0, 105])
        return fig

    _diet_fig = _bar(_diet, "Optimal crude diet (base economics, LP — severity 1.0)")
    _switch = sorted(SC["switch_share"].items(), key=lambda kv: -kv[1])
    _switch_fig = _bar(
        _switch, "Regime switch — share of 10k price scenarios each crude is optimal in"
    )
    mo.vstack([_diet_fig, _switch_fig])
    return


@app.cell
def _(mo):
    # Scenario risk (Phase 5) — precomputed table + the committed fan/tornado
    # figures, which the dashboard previously never rendered.
    import json as _sjson
    from pathlib import Path as _spath

    import marimo as _mo_img

    summary = _sjson.loads(_spath("data/derived/scenarios_phase5.json").read_text(encoding="utf-8"))
    p_loss = summary["probability_of_loss"]
    _risk_md = _mo_img.md(
        f"""
        ## Scenario risk (10,000 correlated price scenarios)

        Historical block bootstrap over real EIA monthly co-moves (Brent + USGC
        products, 2015–2025); each draw **re-optimizes the blend** via the exact
        LP. Precomputed summary (`scripts/run_scenarios.py`, deterministic,
        seed {summary["seed"]}):

        | Metric (re-optimized per draw) | Value |
        |---|---|
        | Base margin | ${summary["base_margin"]:.2f}/bbl |
        | Mean ± σ | ${summary["mean_margin"]:.2f} ± {summary["margin_std"]:.2f} |
        | **VaR 5%** | ${summary["var_pct"]:.2f} |
        | **CVaR 5%** | ${summary["cvar_pct"]:.2f} |
        | P(loss) | {p_loss:.1%} |
        | Fixed-blend mean (no re-opt) | ${summary["fixed_blend_mean"]:.2f} |
        | **Value of re-optimization** | **${summary["reopt_value_mean"]:.2f}/bbl** |
        | Fixed-blend CVaR 5% | ${summary["fixed_cvar_pct"]:.2f} (vs {summary["cvar_pct"]:.2f}) |
        """
    )
    _fan = _mo_img.image("docs/assets/margin_fan.png", width=720)
    _tornado = _mo_img.image("docs/assets/tornado_margin.png", width=720)
    mo.vstack([_risk_md, _fan, _tornado])
    return


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
    CURVES,
    PRICE_VEC,
    SURROGATE_INFO,
    baseline_severity,
    crude_quals,
    COSTS,
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
    # lp_inputs feeds the bridge-exact LP bar even when DE runs through the
    # surrogate — the honest comparison the dashboard exists to show.
    from dangote_opt.optimization.de_driver import DE_BUDGET_S
    from dangote_opt.optimization.de_driver import optimize_blend as run_opt

    result = run_opt(
        objective, lp_inputs=(CURVES, COSTS, PRICE_VEC, crude_quals)
    )
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
        ### Deep re-optimization (live run)

        *Bridge yields · Brent costs · USGC prices · quality specs*

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
def _(PRICES, SURROGATE_INFO, mo):
    # Assumptions & methodology — collapsed by default so the story stays clean
    # but every number's provenance is one click away.
    if SURROGATE_INFO is not None:
        lco_note = (
            "Leave-crude-out honesty finding: jet R² collapses to "
            f"{SURROGATE_INFO['cv_leave_crude_out']['yield_jet']['r2']:.2f} — trees cannot "
            "extrapolate below a held-out crude's range; deployment never needs "
            "unseen crudes (models/model_card.md)."
        )
    else:
        lco_note = "Surrogate metrics available in models/model_card.md."

    mo.accordion(
        {
            "## Model & validation": mo.md(
                f"""
                - **Stage-1 bridge:** TBP cut-point integration + FCC conversion
                40→80% linear in severity (Gary & Handwerk cited ranges);
                ground-truthed to ±0.2 vol% vs published cut tables.
                - **Surrogate:** ETR 150×14×4, dual CV — random 5-fold (headline)
                + leave-crude-out (honesty), always reported together. {lco_note}
                - **DE = LP to <$0.005/bbl:** the bridge physics are affine in
                severity, so the exact LP is the honest bar and DE meets it
                (methodology §6a) — the "is DE actually earning its keep?"
                question is answered structurally, not rhetorically.
                """
            ),
            "## Data provenance (real vs assumed)": mo.md(
                f"""
                - **REAL:** crude assays (TotalEnergies / ExxonMobil sheets, row 3);
                product prices — gasoline ${PRICES.get("gasoline", float("nan")):.2f} /
                diesel ${PRICES.get("diesel", float("nan")):.2f} / jet
                ${PRICES.get("jet", float("nan")):.2f}/bbl (EIA USGC 12-mo, row 2);
                Brent cost anchor $69.10/bbl (row 9).
                - **ASSUMED:** per-grade differentials (quality-rationale table in
                `data/costs.py`; refresh path: OPEC MOMR actuals).
                - **PLACEHOLDER:** petrochem pool price (no citable EIA spot for the
                LPG/propylene/residue basket — probed; documented in prices.py).
                - Every constant cited in `docs/methodology.md`; nothing invented
                silently.
                """
            ),
            "## Reproduce everything": mo.md(
                """
                ```bash
                uv sync                                        # locked env (uv.lock committed)
                PYTHONUTF8=1 uv run pytest                     # 137 offline tests
                PYTHONUTF8=1 uv run python scripts/train_surrogate.py    # ~5 s, deterministic
                PYTHONUTF8=1 uv run python scripts/sensitivity_study.py  # 100 DE seeds
                PYTHONUTF8=1 uv run python scripts/run_scenarios.py      # 10k Monte Carlo
                ```
                All randomness is seeded (20260919 / 42); artifacts in
                `data/derived/` are committed and regenerate byte-identically.
                """
            ),
        }
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---
        **Transparency:** methodology demo on public data — not Dangote's actual
        operations. Real: assays, EIA USGC product prices, Brent anchor, FX/WTI
        ticker context. Assumed/placeholders as disclosed above and in
        `docs/data_provenance.md`. Repo:
        [batestguy/dangote-refinery-optimizer](https://github.com/batestguy/dangote-refinery-optimizer).
        """
    )
    return


if __name__ == "__main__":
    app.run()
