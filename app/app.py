"""Dangote Refinery Blend Optimizer — marimo app (POC).

The file that deploys to HuggingFace Spaces unchanged (Phase 6, spec §3.7).
Runs locally with:  uv run marimo run app/app.py

NOTE: uses the placeholder linear yield model until the Phase 3 ETR surrogate
lands. All numbers shown are methodology-demo outputs, not real Dangote data.
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
    from dangote_opt.config import CONFIG
    from dangote_opt.optimization.objective import RefineryObjective, simplex_repair

    # Mock slate — replaced by real parsed assays in Phase 1 (docs/data_provenance.md)
    CRUDES = ["Bonny Light*", "Forcados*", "Qua Iboe*", "Arab Light*", "Urals*"]
    objective = RefineryObjective(
        crude_apis=np.array([33.5, 30.5, 33.8, 33.3, 31.7]),
        crude_sulfurs=np.array([0.16, 0.24, 0.13, 2.9, 1.3]),
        crude_costs=np.array([78.0, 77.5, 78.5, 72.0, 68.0]),
        product_prices=np.array([CONFIG.default_prices[p] for p in CONFIG.products]),
    )
    return CONFIG, CRUDES, objective, simplex_repair


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
        ### Optimal crude diet (placeholder model — demo only)
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
        **Transparency:** *-marked crude names/costs are illustrative placeholders;
        yields come from a linear placeholder model. This is a methodology demo on
        public/synthetic data — not Dangote's actual operations (spec §7).
        Placeholder model is replaced by the ETR surrogate in Phase 3.
        """
    )
    return


if __name__ == "__main__":
    app.run()
