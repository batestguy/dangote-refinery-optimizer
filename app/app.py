"""Dangote Refinery Blend Optimizer — marimo dashboard (Phase 6).

The file that deploys to HuggingFace Spaces unchanged (spec §3.7).
Runs locally with:  uv run marimo run app/app.py

Design system: light corporate theme in the Dangote brand palette — navy
indigo #171D64 ("Lucky Point", Pantone 2756C) + flare red #F0513A ("Flare",
Pantone 7625C), per the Dangote Cement logo colors (schemecolor.com;
"The Dangote Color Strategy", LinkedIn) — with mono numerals (fonts load
async from Google Fonts with safe fallbacks, so cold start is never blocked).
Every section is numbered and
captioned so a first-time visitor knows what to look at and what each result
means; the only click-gated part is the deep re-optimization.

Cold-start discipline (HF Spaces sleep ~48 h): the page renders its whole
static story from committed artifacts first; live feeds degrade to timestamped
stale/snapshot values; nothing shows a number without provenance.

Methodology demo on public data — not real Dangote operations (spec §7).
"""

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
async def _():
    import sys

    import marimo as mo

    # WASM bootstrap (GitHub Pages / Pyodide). Every other cell depends on this
    # one through `mo`/`np`, so it finishes before any of them run. Locally and
    # on the Space it is a no-op. In the browser there is no repo on disk, so:
    #   1. install the app's own wheel (deps=False: its metadata pulls
    #      datasets/pdfplumber, which are build-time only and don't load in
    #      Pyodide) plus the runtime deps the package imports internally;
    #   2. copy the committed artifacts from public/ into the virtual FS at
    #      their repo-relative paths, so every Path(...) read below works
    #      unchanged. Keep _WASM_FILES in sync with app/public/.
    if sys.platform == "emscripten":
        from pathlib import Path as _wPath

        import micropip
        from pyodide.http import pyfetch

        mo.output.replace(
            mo.callout(
                mo.md(
                    "**Loading the optimizer in your browser…** First visit downloads "
                    "a full scientific Python stack and can take **up to ~5 minutes** "
                    "(longer on mobile data). Keep this tab open; later visits are "
                    "faster."
                ),
                kind="info",
            )
        )
        import importlib
        import importlib.util

        _base = str(mo.notebook_location()).rstrip("/")
        # Pyodide's package loader only *logs* a failed download (flaky CDN,
        # mobile data) instead of raising, which used to leave a silently
        # broken page. Verify each import and retry what is missing.
        _needed = {
            "numpy": "numpy",
            "pandas": "pandas",
            "pyarrow": "pyarrow",
            "scipy": "scipy",
            "sklearn": "scikit-learn",
            "plotly": "plotly",
            "dotenv": "python-dotenv",
            "requests": "requests",
        }
        for _attempt in range(3):
            importlib.invalidate_caches()
            _missing = [
                _pkg for _mod, _pkg in _needed.items() if importlib.util.find_spec(_mod) is None
            ]
            if not _missing:
                break
            try:
                await micropip.install(_missing)
            except Exception:  # noqa: BLE001 — re-checked below
                pass
        importlib.invalidate_caches()
        _missing = [
            _pkg for _mod, _pkg in _needed.items() if importlib.util.find_spec(_mod) is None
        ]
        mo.stop(
            bool(_missing),
            mo.callout(
                mo.md(
                    "**Couldn't download all of the Python packages** "
                    f"({', '.join(_missing)}). This is usually a flaky connection: "
                    "please reload the page."
                ),
                kind="danger",
            ),
        )
        await micropip.install(
            f"{_base}/public/wheels/dangote_refinery_optimizer-0.1.0-py3-none-any.whl",
            deps=False,
        )
        _WASM_FILES = [
            "data/derived/costs_phase2.json",
            "data/derived/prices_phase2.json",
            "data/derived/scenarios_phase5.json",
            "data/derived/sensitivity_phase4.json",
            "data/derived/slate_phase1.parquet",
            "data/derived/ticker_latest.json",
            "docs/assets/credited/cdu_unit.jpg",
            "docs/assets/credited/procedures_a.jpg",
            "docs/assets/credited/procedures_b.jpg",
            "docs/assets/credited/procedures_c.jpg",
            "docs/assets/credited/refinery_site_hero.jpg",
            "docs/assets/margin_fan.png",
        ]
        for _rel in _WASM_FILES:
            _resp = await pyfetch(f"{_base}/public/{_rel}")
            if not _resp.ok:
                raise RuntimeError(f"WASM bootstrap: {_rel} -> HTTP {_resp.status}")
            _dest = _wPath(_rel)
            _dest.parent.mkdir(parents=True, exist_ok=True)
            _dest.write_bytes(await _resp.bytes())
        mo.output.clear()

    import numpy as np

    return mo, np


@app.cell
def _(mo):
    # Design system — one <style> block, injected once, applies app-wide.
    # Plain string (NOT f-string): CSS braces would break f-string parsing.
    # The hero photo (the actual Dangote site at Lekki, CC BY-SA 4.0) is
    # embedded as a base64 data URI so it travels inside app.py — the file that
    # deploys to HF Spaces unchanged — with zero extra requests at cold start.
    import base64 as _base64
    from pathlib import Path as _Path

    hero_b64 = _base64.b64encode(
        _Path("docs/assets/credited/refinery_site_hero.jpg").read_bytes()
    ).decode()
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
      /* Brand palette — Dangote logo colors (cited): navy indigo #171D64
         ("Lucky Point", Pantone 2756C) + flare red #F0513A ("Flare", Pantone
         7625C). Sources: schemecolor.com/dangote-cement-logo-colors.php and
         "The Dangote Color Strategy" (LinkedIn). Supporting tints derived. */
      --bg: #f7f8fc;          /* paper white with a navy breath */
      --surface: #ffffff;
      --surface-2: #eef0f9;
      --border: #d8dcef;
      --text: #171d3c;        /* near-black navy ink */
      --muted: #5c6191;
      --navy: #171d64;        /* brand primary */
      --red: #f0513a;         /* brand accent */
      --red-dim: #c93a26;     /* flare, darkened for rules on white */
      --amber: #c77700;       /* warning only (stale badge) */
      --amber-dim: #8a5700;
      --green: #0e9f6e;
      --teal: #0f766e;
      --mono: 'IBM Plex Mono', ui-monospace, monospace;
      --cond: 'Barlow Condensed', 'Arial Narrow', sans-serif;
      --sans: 'IBM Plex Sans', system-ui, sans-serif;
    }
    html, body { background: var(--bg) !important; }
    /* marimo's shell: .bg-background is the Tailwind token that paints the
       gutters/header — verified via DOM inspection, overridden here.
       .marimo-cell wrappers also paint their own background; cells go
       transparent so the page background shows through between sections. */
    .bg-background { background-color: var(--bg) !important; }
    .marimo-cell { background-color: transparent !important; }
    body, .prose, .markdown p, .markdown li { color: var(--text); }
    h1, h2, h3 { color: var(--text); font-family: var(--cond); letter-spacing: .02em; }
    code { color: var(--navy); font-family: var(--mono); font-size: .88em;
           background: var(--surface-2); border-radius: 4px; padding: 1px 5px; }
    table { border-collapse: collapse; width: 100%; font-family: var(--mono);
            font-size: 13.5px; }
    th { text-align: left; color: var(--navy); font-weight: 600;
         border-bottom: 2px solid var(--red); padding: 7px 10px;
         text-transform: uppercase; letter-spacing: .06em; font-size: 11.5px; }
    td { padding: 7px 10px; border-bottom: 1px solid var(--border);
         color: var(--text); }
    tr:hover td { background: var(--surface-2); }
    img { border-radius: 10px; border: 1px solid var(--border); }

    /* hero */
    /* hero — the logo's composition: navy field, red arc on top */
    .hero { position: relative; border: 1px solid var(--border); border-top: 6px solid var(--red);
            background: linear-gradient(105deg, rgba(23,29,100,.96) 0%,
                        rgba(23,29,100,.88) 42%, rgba(23,29,100,.62) 100%),
                        url('data:image/jpeg;base64,__HERO_B64__') center 38%/cover no-repeat;
            border-radius: 14px; padding: 30px 30px; min-height: 230px; }
    .hero h1 { font-size: 44px; line-height: 1; margin: 0 0 6px;
               text-transform: uppercase; color: #fff; }
    .hero h1 .oil { color: #ff8d7a; }
    .hero p { margin: 6px 0 12px; color: #cdd2f2; max-width: 68ch; }
    .hero p b { color: #fff; }
    .h-credit { position: absolute; right: 12px; bottom: 10px;
                font-family: var(--mono); font-size: 10px; letter-spacing: .04em;
                color: rgba(255,255,255,.85); background: rgba(23,29,60,.55);
                border-radius: 6px; padding: 3px 8px; }
    .h-credit a { color: #fff; }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .chip { font-family: var(--mono); font-size: 11px; letter-spacing: .08em;
            color: #fff; border: 1px solid rgba(240,81,58,.9);
            border-radius: 999px; padding: 3px 10px; background: rgba(240,81,58,.22); }

    /* start-here stepper */
    .stepper { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    .step { flex: 1 1 200px; background: rgba(255,255,255,.94); border: 1px solid var(--border);
            border-radius: 10px; padding: 10px 12px; font-size: 13px;
            color: var(--muted); }
    .step b { color: var(--text); display: block; }
    .step .n { font-family: var(--mono); color: var(--red); font-size: 12px; }

    /* numbered section banners — the directional layer */
    .sec { display: flex; gap: 14px; align-items: flex-start; margin: 26px 0 10px;
           border-bottom: 1px solid var(--border); padding-bottom: 8px; }
    .sec .idx { font-family: var(--mono); font-size: 15px; color: #fff;
                background: var(--navy); border-radius: 6px; padding: 3px 8px;
                font-weight: 600; }
    .sec h2 { margin: 0; font-size: 26px; text-transform: uppercase;
              letter-spacing: .04em; }
    .sec .sub { margin: 2px 0 0; color: var(--muted); font-size: 13.5px; }

    /* KPI tiles */
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px,1fr));
                gap: 12px; }
    .kpi { background: var(--surface); border: 1px solid var(--border);
           border-radius: 12px; padding: 14px 16px; position: relative; overflow: hidden; }
    .kpi::before { content: ''; position: absolute; inset: 0 auto 0 0; width: 4px;
                   background: var(--accent, var(--navy)); }
    .kpi .label { font-family: var(--cond); text-transform: uppercase;
                  letter-spacing: .1em; font-size: 12.5px; color: var(--muted); }
    .kpi .value { font-family: var(--mono); font-size: 30px; font-weight: 600;
                  color: var(--accent, var(--navy)); margin: 4px 0 2px; }
    .kpi .note { font-size: 12px; color: var(--muted); line-height: 1.45; }

    /* ticker tape */
    .tape { display: flex; gap: 12px; flex-wrap: wrap; }
    .quote { flex: 1 1 260px; background: var(--surface); border: 1px solid var(--border);
             border-radius: 12px; padding: 12px 16px; }
    .quote .q-label { font-family: var(--cond); text-transform: uppercase;
                      letter-spacing: .1em; color: var(--muted); font-size: 12.5px; }
    .quote .q-value { font-family: var(--mono); font-size: 26px; font-weight: 600;
                      color: var(--text); }
    .quote .q-asof { font-family: var(--mono); font-size: 11.5px; color: var(--muted); }
    .pill { font-family: var(--mono); font-size: 11px; border-radius: 999px;
            padding: 2px 9px; margin-left: 8px; vertical-align: middle; }
    .pill.live { color: var(--green); border: 1px solid var(--green); background: rgba(61,220,151,.08); }
    .pill.stale { color: var(--amber); border: 1px solid var(--amber);
                  background: rgba(199,119,0,.07); }
    .pill.snap { color: var(--teal); border: 1px solid var(--teal); background: rgba(45,212,191,.07); }
    .legend { margin-top: 8px; font-size: 12px; color: var(--muted);
              font-family: var(--mono); }

    /* callouts + result cards */
    .callout { border: 1px solid var(--border); border-left: 4px solid var(--navy);
               background: var(--surface); border-radius: 10px; padding: 10px 14px;
               font-size: 13px; color: var(--muted); margin-top: 10px; }
    .callout.accent { border-left-color: var(--red); }
    .card { background: var(--surface); border: 1px solid var(--border);
            border-radius: 12px; padding: 16px 18px; }
    .bar-de { color: var(--green); font-weight: 600; }

    /* footer */
    .foot { margin-top: 30px; border-top: 1px solid var(--border); padding-top: 12px;
            color: var(--muted); font-size: 12.5px; }
    .photo { border-radius: 12px; border: 1px solid var(--border); width: 100%;
             height: auto; display: block; }
    .credit { font-family: var(--mono); font-size: 10.5px; color: var(--muted);
              margin-top: 5px; }
    .credit a { color: var(--navy); }
    .duo { display: grid; grid-template-columns: 1.25fr 1fr; gap: 14px;
           align-items: start; }
    .duo .cell { background: var(--surface); border: 1px solid var(--border);
                 border-radius: 12px; padding: 10px 12px 12px;
                 position: relative; }
    .duo .cap { font-size: 13px; color: var(--muted); margin-top: 8px;
                line-height: 1.5; position: relative; z-index: 1; }
    .duo .cap b { color: var(--text); }

    /* procedures photo strip */
    .strip { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
             margin-top: 12px; }
    .strip .s-item { background: var(--surface); border: 1px solid var(--border);
                     border-radius: 12px; padding: 8px 8px 9px; }
    .strip img { width: 100%; height: 190px; object-fit: cover; border-radius: 8px;
                 border: 1px solid var(--border); display: block; }
    .strip .s-credit { font-family: var(--mono); font-size: 10.5px; color: var(--muted);
                       margin-top: 6px; }
    .strip .s-credit a { color: var(--navy); }
    .strip .s-cap { grid-column: 1 / -1; font-size: 13px; color: var(--muted); }
    .strip .s-cap b { color: var(--text); }
    @media (max-width: 900px) {
      .strip, .duo { grid-template-columns: 1fr; }
      .hero { padding: 22px 18px; }
      .hero h1 { font-size: 34px; }
    }

    /* static figure that keeps a readable size on phones: scrolls sideways
       inside its own box instead of shrinking the labels */
    .figscroll { overflow-x: auto; -webkit-overflow-scrolling: touch;
                 background: var(--surface); border: 1px solid var(--border);
                 border-radius: 12px; padding: 8px; max-width: 780px; }
    .figscroll img { display: block; width: 100%; min-width: 640px; height: auto; }
    .swipe { display: none; font-family: var(--mono); font-size: 11px;
             color: var(--muted); margin: 4px 0 0; }
    @media (max-width: 700px) { .swipe { display: block; } }
    .foot a { color: var(--navy); }
    .deerflow { font-family: var(--mono); font-size: 11px; color: var(--muted);
                opacity: .75; text-decoration: none; }
    .deerflow:hover { opacity: 1; color: var(--red); }
    </style>
    """
    mo.Html(css.replace("__HERO_B64__", hero_b64))
    return


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
    from dangote_opt.optimization.objective import RefineryObjective

    # REAL slate — parsed published assays (docs/data_provenance.md row 3).
    df = pd.read_parquet("data/derived/slate_phase1.parquet")
    records = frame_to_records(df)
    CRUDES = [r.name for r in records]
    CURVES = [np.array(r.tbp_curve, dtype=float) for r in records]
    CRUDE_CUTS = np.array([tbp_cut_fractions(c) for c in CURVES])
    LIGHT_NAP = light_naphtha_fractions(CURVES)

    # REAL cost anchor — EIA Brent trailing-12m average + documented per-grade
    # differentials (docs/data_provenance.md row 9; differentials are ASSUMED).
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
    # petrochem stays on the disclosed CONFIG placeholder.
    try:
        price_frame = usgc_prices_frame(dotenv_values(".env").get("EIA_API_KEY", "").strip() or "")
        PRICES = product_prices(price_frame)
    except Exception:  # noqa: BLE001 — offline fallback to the committed artifact
        price_sidecar = json.loads(
            Path("data/derived/prices_phase2.json").read_text(encoding="utf-8")
        )
        PRICES = price_sidecar["prices_usd_bbl"]
    PRICE_VEC = np.array([PRICES[p] for p in CONFIG.products])

    # REAL quality model — pool qualities from the bridge's component streams.
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

    # Phase 3 surrogate when trained — the bridge remains source of truth and
    # fallback; the quality model stays bridge-exact (cheap, surrogate ≈ bridge).
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
        COSTS,
        CRUDE_CUTS,
        CRUDES,
        CURVES,
        PRICES,
        PRICE_VEC,
        SC,
        SENS,
        SURROGATE_INFO,
        crude_quals,
        objective,
    )


@app.cell
def _(mo):
    mo.Html(
        """
        <div class="hero">
          <h1>Crude Blend <span class="oil">Optimizer</span></h1>
          <p><b>Refinery-scale feedstock planning as a working console.</b> Five real
          published crude assays flow through a cited TBP cut-point bridge into four
          product pools; a differential-evolution optimizer picks the diet and the FCC
          severity — and is benchmarked live against an exact linear-program optimum,
          the honest bar any method must meet.</p>
          <div class="chips">
            <span class="chip">5 REAL ASSAYS</span>
            <span class="chip">EIA PRICES</span>
            <span class="chip">QUALITY SPECS ENFORCED</span>
            <span class="chip">DE ≡ LP</span>
            <span class="chip">137 OFFLINE TESTS</span>
          </div>
          <div class="h-credit">Photo: GodwinPaya, CC BY-SA 4.0, via
            <a href="https://commons.wikimedia.org/wiki/File:Palm_trees_beside_Dangote_Refinery_at_leki_village_Lagos_Nigeria.jpg" target="_blank">Commons</a></div>
          <div class="stepper">
            <div class="step"><span class="n">START 1</span><b>Read the headline tiles</b>
              The economics already computed — deterministic, seeded.</div>
            <div class="step"><span class="n">START 2</span><b>Scroll the numbered sections</b>
              Every banner says what you're looking at and why it matters.</div>
            <div class="step"><span class="n">START 3</span><b>Press ⚡ Run (section 05)</b>
              Re-optimize live, then compare DE to the LP honest bar.</div>
          </div>
        </div>
        """
    )
    return


@app.cell
def _(SC, SENS, SURROGATE_INFO, mo):
    # 01 · Headline tiles — every value precomputed in committed artifacts.
    if SURROGATE_INFO is not None:
        _min_r2 = min(m["r2"] for m in SURROGATE_INFO["cv_random_5fold"].values())
        _lco_jet = SURROGATE_INFO["cv_leave_crude_out"]["yield_jet"]["r2"]
        _model_value = f"{_min_r2:.3f}"
        _model_note = (
            f"min random 5-fold R² across products. Honesty check: jet drops to "
            f"{_lco_jet:.2f} leave-crude-out (trees can't extrapolate) — disclosed "
            f"in the model card."
        )
    else:
        _model_value = "bridge"
        _model_note = (
            "surrogate not trained here — the exact bridge runs instead, same "
            "optimum (train it: scripts/train_surrogate.py, ~5 s)."
        )

    _risk = (
        f"VaR5 ${SC['var_pct']:.2f} · CVaR5 ${SC['cvar_pct']:.2f} · "
        f"P(loss) {SC['probability_of_loss']:.1%}"
    )

    mo.Html(
        f"""
        <div class="sec"><span class="idx">01</span><div>
          <h2>Headline results</h2>
          <p class="sub">The economics, precomputed and seeded — what the optimizer
          achieves and why it's trustworthy. No model load, no network.</p>
        </div></div>
        <div class="kpi-grid">
          <div class="kpi" style="--accent: var(--red)">
            <div class="label">Blend margin</div>
            <div class="value">${SC["base_margin"]:.2f}<span style="font-size:14px">/bbl</span></div>
            <div class="note">LP optimum at base prices — diet ≈ 100% Alaska North
            Slope, FCC at max severity.</div>
          </div>
          <div class="kpi" style="--accent: var(--green)">
            <div class="label">Uplift vs equal-weight</div>
            <div class="value">{SENS["uplift_vs_equal_weight"]:+.1%}</div>
            <div class="note">over the naive 20%-each blend · 100-seed sweep,
            margin σ ${SENS["margin_std"]:.3f} (deterministic engine).</div>
          </div>
          <div class="kpi" style="--accent: var(--green)">
            <div class="label">Value of re-optimizing</div>
            <div class="value">+${SC["reopt_value_mean"]:.2f}<span style="font-size:14px">/bbl</span></div>
            <div class="note">mean gain from re-optimizing as prices move — and it
            flips the loss tail positive (section 04).</div>
          </div>
          <div class="kpi" style="--accent: var(--red)">
            <div class="label">Downside risk · 10k scenarios</div>
            <div class="value" style="font-size:20px">{_risk}</div>
            <div class="note">historical block bootstrap of real EIA co-moves;
            only {SC["probability_of_loss"]:.1%} of price worlds lose money.</div>
          </div>
          <div class="kpi" style="--accent: var(--navy)">
            <div class="label">Surrogate quality</div>
            <div class="value">{_model_value}</div>
            <div class="note">{_model_note}</div>
          </div>
        </div>
        """
    )
    return


@app.cell
def _(mo):
    # Live ticker — data logic identical to the verified version; new shell.
    import json as _tjson
    from pathlib import Path as _tpath

    from dotenv import dotenv_values as _dotenv_values

    from dangote_opt.data.ticker import fetch_ngn_usd_rate as _fetch_fx
    from dangote_opt.data.ticker import fetch_wti_spot as _fetch_wti

    _snapshot = _tjson.loads(_tpath("data/derived/ticker_latest.json").read_text(encoding="utf-8"))

    def _mark(live_q, snap_q):
        """(quote, badge) — live quote if reachable, else the staged snapshot."""
        if live_q is not None:
            return live_q, "live" if not live_q.stale else "stale"
        q = type("Q", (), {})()
        q.value, q.as_of, q.source = (snap_q["value"], snap_q["as_of"], snap_q["source"])
        return q, "snap"

    _fx_live = _wti_live = None
    try:
        _fx_live = _fetch_fx()
    except Exception:  # noqa: BLE001 — ticker must never break the dashboard
        pass
    try:
        _wti_live = _fetch_wti(_dotenv_values(".env").get("EIA_API_KEY", "").strip())
    except Exception:  # noqa: BLE001
        pass

    _fx, _fx_cls = _mark(_fx_live, _snapshot["quotes"]["ngn_usd"])
    _wti, _wti_cls = _mark(_wti_live, _snapshot["quotes"]["wti_spot"])

    mo.Html(
        f"""
        <div class="sec"><span class="idx">02</span><div>
          <h2>Live market tape</h2>
          <p class="sub">Context prices, refreshed on load. Display-only — neither
          feed enters the optimization (USD single-period price-taker, spec §7).</p>
        </div></div>
        <div class="tape">
          <div class="quote">
            <div class="q-label">NGN / USD FX
              <span class="pill {_fx_cls}">{"🟢 " if _fx_cls == "live" else ""}{_fx_cls.upper()}</span></div>
            <div class="q-value">{_fx.value:,.2f} <span style="font-size:14px">₦/$</span></div>
            <div class="q-asof">as of {_fx.as_of}</div>
          </div>
          <div class="quote">
            <div class="q-label">WTI crude spot
              <span class="pill {_wti_cls}">{"🟢 " if _wti_cls == "live" else ""}{_wti_cls.upper()}</span></div>
            <div class="q-value">${_wti.value:,.2f}<span style="font-size:14px">/bbl</span></div>
            <div class="q-asof">as of {_wti.as_of}</div>
          </div>
        </div>
        <div class="legend">STATUS — 🟢 LIVE: fetched just now · STALE: cached value,
        feed unreachable · SNAP: committed snapshot ({_snapshot["generated_utc"][:10]}).
        FX: open.er-api.com (row 8, 1 h cache) · WTI: EIA daily spot, Cushing.</div>
        """
    )
    return


@app.cell
def _(SC, mo):  # 03 · Charts — light brand plotly template (navy/red).
    import base64 as _cbase64
    from pathlib import Path as _cPath

    import plotly.express as _px
    import plotly.graph_objects as _go
    import plotly.io as _pio

    _cdu_b64 = _cbase64.b64encode(_cPath("docs/assets/credited/cdu_unit.jpg").read_bytes()).decode()
    _p1_b64 = _cbase64.b64encode(
        _cPath("docs/assets/credited/procedures_a.jpg").read_bytes()
    ).decode()
    _p2_b64 = _cbase64.b64encode(
        _cPath("docs/assets/credited/procedures_b.jpg").read_bytes()
    ).decode()
    _p3_b64 = _cbase64.b64encode(
        _cPath("docs/assets/credited/procedures_c.jpg").read_bytes()
    ).decode()

    _pio.templates["dangote"] = _go.layout.Template(
        layout=_go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono, monospace", color="#3a3f6e", size=12),
            xaxis=dict(gridcolor="#d8dcef", zerolinecolor="#d8dcef"),
            yaxis=dict(gridcolor="#d8dcef", zerolinecolor="#d8dcef"),
        )
    )
    _pio.templates.default = "dangote"

    def _bar(pairs, color, value_fmt):
        names = [k for k, _ in pairs]
        vals = [v * 100 for _, v in pairs]
        fig = _px.bar(
            x=vals,
            y=names,
            orientation="h",
            text=[value_fmt(v) for v in vals],
        )
        fig.update_traces(
            marker_color=color,
            marker_line_color="#ffffff",
            marker_line_width=1,
            textposition="outside",
            cliponaxis=False,
        )
        fig.update_layout(
            height=52 + 34 * len(names),
            margin=dict(l=150, r=40, t=6, b=4),
            xaxis_title="share of optimal blends (%)",
            yaxis=dict(autorange="reversed"),
            xaxis_range=[0, 112],
        )
        # no toolbar: on phones it sits on top of the axis labels
        return mo.ui.plotly(fig, config={"displayModeBar": False})

    _diet = sorted(SC["base_blend"].items(), key=lambda kv: -kv[1])
    _switch = sorted(SC["switch_share"].items(), key=lambda kv: -kv[1])
    _cdu_note = (
        '<div class="cap" style="margin-top:2px"><b style="font-size:15px">'
        "The choice at a glance</b></div>"
        '<table style="margin-top:6px">'
        "<tr><th>Decision</th><th>Optimum</th></tr>"
        f"<tr><td>Diet (base)</td><td>{_diet[0][0]} {_diet[0][1]:.0%}</td></tr>"
        "<tr><td>FCC severity</td><td>1.00 — max conversion</td></tr>"
        f"<tr><td>Margin</td><td><b>${SC['base_margin']:.2f}/bbl</b></td></tr>"
        "<tr><td>Honest bar</td><td>exact LP — met to &lt;$0.005</td></tr>"
        "</table>"
        '<div class="cap">Why one crude? The optimizer buys the barrel with the '
        "best margin — ANS&#39;s sour discount beats the sweetening cost. "
        "Section 04 shows when that flips.</div>"
    )
    _section03 = (
        '<div class="sec"><span class="idx">03</span><div>'
        "<h2>What the optimizer chose</h2>"
        '<p class="sub">Left: the single best diet at base prices. Right: '
        "how often each crude is optimal across 10,000 price scenarios — "
        "the diet genuinely switches with prices.</p></div></div>"
        '<div class="duo">'
        '<div class="cell">'
        '<img class="photo" src="data:image/jpeg;base64,__CDU_B64__" '
        'alt="Vessel at Dangote refinery site, Lagos — crude arriving by sea at Lekki">'
        '<div class="cap"><b>Where the barrel comes in</b> — a vessel at the '
        "Dangote refinery site, Lekki: the crude our optimizer buys is one of "
        "these cargoes. Inside the plant, the FCC converts 40→80% of the VGO "
        "cut as severity rises (cited range) — the severity variable our "
        "solver tunes.</div>"
        '<div class="credit">Photo: GodwinPaya, CC BY-SA 4.0, via '
        '<a href="https://commons.wikimedia.org/wiki/File:Vessel_at_Dangote_refinery_site,_Lagos.jpg" '
        'target="_blank">Wikimedia Commons</a></div>'
        "</div>"
        '<div class="cell">' + _cdu_note + "</div></div>"
    ).replace("__CDU_B64__", _cdu_b64)
    _strip = (
        (
            '<div class="strip">'
            '<div class="s-cap"><b>Inside the plant</b> — on site at the Dangote '
            "Refinery, Lekki (2022): Aliko Dangote receiving a guest at the "
            "plant, delivery of the 3,000-ton RFCC regenerator (people give the "
            "scale), and the preheating train (desalting + distillation "
            "column).</div>"
            '<div class="s-item">'
            '<img src="data:image/jpeg;base64,__P1__" alt="Aliko Dangote on site at the Dangote Refinery, Lekki">'
            '<div class="s-credit">Photo: Maxwell, CC BY-SA 4.0, via '
            '<a href="https://commons.wikimedia.org/wiki/File:Zulfi_Azad_with_Aliko_Dangote.jpg" target="_blank">Commons</a></div>'
            "</div>"
            '<div class="s-item">'
            '<img src="data:image/jpeg;base64,__P2__" alt="Delivery of the 3,000-ton RFCC regenerator at Dangote Refinery, Lekki — people beside the vessel for scale">'
            '<div class="s-credit">Photo: FrankvEck, CC BY-SA 4.0, via '
            '<a href="https://commons.wikimedia.org/wiki/File:Regenerator.jpg" target="_blank">Commons</a></div>'
            "</div>"
            '<div class="s-item">'
            '<img src="data:image/jpeg;base64,__P3__" alt="Preheating train — desalting and distillation column, Dangote Refinery, Lekki">'
            '<div class="s-credit">Photo: FrankvEck, CC BY-SA 4.0, via '
            '<a href="https://commons.wikimedia.org/wiki/File:Cdu-dangote-lekki3.jpg" target="_blank">Commons</a></div>'
            "</div>"
            "</div>"
        )
        .replace("__P1__", _p1_b64)
        .replace("__P2__", _p2_b64)
        .replace("__P3__", _p3_b64)
    )
    mo.vstack(
        [
            mo.Html(_section03),
            _bar(_diet, "#171d64", lambda v: f"{v:.1f}%"),
            _bar(_switch, "#f0513a", lambda v: f"{v:.1f}%" if v >= 1 else f"{v:.1f}%"),
            mo.Html(
                '<div class="callout accent"><b>How to read:</b> Alaska North Slope '
                "wins at base prices (sour discount &gt; sweetening cost), but "
                "Forcados takes over in ~48% of price worlds — the two-regime diet "
                "is the central economic trade-off.</div>"
            ),
            mo.Html(_strip),
        ]
    )
    return


@app.cell
def _(mo):
    # 04 · Risk — precomputed table + committed figures (rendered as plates).
    import base64 as _rb64
    import json as _sjson
    from pathlib import Path as _spath

    summary = _sjson.loads(_spath("data/derived/scenarios_phase5.json").read_text(encoding="utf-8"))

    def _risk_img(rel):
        """Inline the PNG as a data URI: works the same locally and in WASM,
        where the first cell has copied it into the virtual FS (a bare path
        would be treated as a page URL the Pyodide worker can't resolve)."""
        _b = _rb64.b64encode(_spath(rel).read_bytes()).decode()
        return f"data:image/png;base64,{_b}"

    def _usd(v):
        """Money with the sign in front: −$3.50, not $-3.50."""
        return f"{'−' if v < 0 else ''}${abs(v):.2f}"

    def _tornado_fig():
        """Interactive tornado from the committed summary: redraws cleanly at
        any width and shows exact values on tap/hover (the PNG could not)."""
        import plotly.graph_objects as _tgo

        _base = summary["base_margin"]
        _items = sorted(summary["tornado"].items(), key=lambda kv: abs(kv[1][1] - kv[1][0]))
        _names = [k.capitalize() for k, _ in _items]
        _lo = [min(v) for _, v in _items]
        _hi = [max(v) for _, v in _items]
        _fig = _tgo.Figure(
            [
                _tgo.Bar(
                    y=_names,
                    x=[_base - v for v in _lo],
                    base=_lo,
                    orientation="h",
                    name="worse than base",
                    marker_color="#f0513a",
                    text=[f"${v:.2f}" for v in _lo],
                    textposition="inside",
                    insidetextanchor="start",
                    hovertemplate="%{y}: $%{base:.2f}/bbl at the adverse −10% shock<extra></extra>",
                ),
                _tgo.Bar(
                    y=_names,
                    x=[v - _base for v in _hi],
                    base=_base,
                    orientation="h",
                    name="better than base",
                    marker_color="#171d64",
                    text=[f"${v:.2f}" for v in _hi],
                    textposition="inside",
                    insidetextanchor="end",
                    hovertemplate="%{y}: %{text}/bbl at the favorable +10% shock<extra></extra>",
                ),
            ]
        )
        _fig.add_vline(
            x=_base,
            line_dash="dash",
            line_color="#171d3c",
            annotation_text=f"base ${_base:.2f}",
            annotation_position="top",
        )
        _fig.update_layout(
            title=dict(
                text="Tornado: ±10% product-price shocks"
                "<br><sup>margin after re-optimizing the blend</sup>",
                x=0,
                xanchor="left",
                font=dict(size=15),
            ),
            barmode="overlay",
            height=360,
            margin=dict(l=10, r=10, t=60, b=40),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(family="IBM Plex Sans, system-ui, sans-serif", color="#3a3f6e", size=12),
            xaxis=dict(title="Re-optimized margin ($/bbl)", gridcolor="#d8dcef", tickprefix="$"),
            yaxis=dict(automargin=True),
            legend=dict(orientation="h", y=-0.22, x=0),
        )
        return _fig

    p_loss = summary["probability_of_loss"]
    _rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in (
            ("Base margin", f"${summary['base_margin']:.2f}/bbl"),
            ("Mean ± σ (10k)", f"${summary['mean_margin']:.2f} ± {summary['margin_std']:.2f}"),
            ("VaR 5%", f"${summary['var_pct']:.2f}"),
            ("CVaR 5%", f"${summary['cvar_pct']:.2f}"),
            ("P(loss)", f"{p_loss:.1%}"),
            ("Fixed-blend mean (no re-opt)", f"${summary['fixed_blend_mean']:.2f}"),
            ("<b>Value of re-optimization</b>", f"<b>+${summary['reopt_value_mean']:.2f}/bbl</b>"),
            (
                "Fixed-blend CVaR 5%",
                f"{_usd(summary['fixed_cvar_pct'])} (vs {_usd(summary['cvar_pct'])})",
            ),
        )
    )
    mo.vstack(
        [
            mo.Html(
                '<div class="sec"><span class="idx">04</span><div>'
                "<h2>Risk — 10,000 correlated scenarios</h2>"
                '<p class="sub">Historical block bootstrap of real EIA monthly '
                "co-moves (12-month blocks, 2015–2025); every draw re-optimizes "
                "the blend via the exact LP. Deterministic, seed "
                f"{summary['seed']}.</p></div></div>"
                '<div class="card"><table>'
                "<tr><th>Metric (re-optimized per draw)</th><th>Value</th></tr>"
                f"{_rows}</table>"
                '<div class="callout"><b>How to read:</b> a fixed blend loses '
                "money in the worst worlds (CVaR −$3.50); re-optimizing per "
                "scenario turns that tail <b>positive</b> — flexibility is a risk "
                "lever, not just a profit lever.</div></div>"
            ),
            mo.Html(
                '<div class="figscroll"><img alt="Margin fan: re-optimized margin '
                "percentiles across 10,000 bootstrapped price scenarios, by 12-month "
                f'Brent change" src="{_risk_img("docs/assets/margin_fan.png")}"></div>'
                '<p class="swipe">↔ swipe the chart to see all of it</p>'
            ),
            mo.ui.plotly(_tornado_fig(), config={"displayModeBar": False}),
            mo.Html(
                '<div class="legend">Fan: margin distribution per year under '
                "bootstrapped prices · Tornado: margin sensitivity to each product "
                "price ±10%, blend re-optimized. Full summary: "
                "data/derived/scenarios_phase5.json</div>"
            ),
        ]
    )
    return


@app.cell
def _(mo):
    # 05 · Controls — the only click-gated section.
    mo.Html(
        '<div class="sec"><span class="idx">05</span><div>'
        "<h2>Run it yourself</h2>"
        '<p class="sub">Set the baseline severity for the equal-weight comparison '
        "(the DE optimizes severity itself), then press Run — ~3–15 s. The "
        "result lands right below.</p></div></div>"
    )
    baseline_severity = mo.ui.slider(
        0.0, 1.0, value=0.5, step=0.01, label="Baseline FCC severity (equal-weight comparison)"
    )
    run = mo.ui.run_button(label="⚡ Run deep optimization")
    mo.vstack([baseline_severity, run])
    return baseline_severity, run


@app.cell
def _(
    CONFIG,
    COSTS,
    CRUDES,
    CURVES,
    PRICE_VEC,
    SURROGATE_INFO,
    baseline_severity,
    crude_quals,
    mo,
    np,
    objective,
    run,
):
    mo.stop(
        not run.value,
        mo.Html(
            '<div class="card" style="border-left:4px solid var(--red)">'
            "<b>Waiting for you:</b> press <b>⚡ Run deep optimization</b> above. "
            "The solver picks the crude diet <i>and</i> the FCC severity, then "
            "checks itself against the exact LP — the honest bar.</div>"
        ),
    )

    from dangote_opt.optimization.de_driver import DE_BUDGET_S
    from dangote_opt.optimization.de_driver import optimize_blend as run_opt

    # lp_inputs feeds the bridge-exact LP bar even when DE runs the surrogate —
    # the honest comparison the dashboard exists to show.
    with mo.status.spinner(
        title="Optimizing…",
        subtitle="Differential evolution, then the exact LP check (a few seconds)",
    ):
        result = run_opt(objective, lp_inputs=(CURVES, COSTS, PRICE_VEC, crude_quals))
    x, sev, margin_de = result.best_x, result.best_severity, result.best_margin
    x_eq = np.full(CONFIG.n_crudes, 1 / CONFIG.n_crudes)
    margin_eq = objective.margin(x_eq, baseline_severity.value)
    uplift = (margin_de - margin_eq) / abs(margin_eq) if margin_eq else float("nan")

    rows = "".join(
        f"<tr><td>{name}</td><td>{xi:.1%}</td></tr>" for name, xi in zip(CRUDES, x, strict=True)
    )
    violations = result.violations
    status = "✅ feasible" if not violations else f"⚠️ {violations}"

    def _b(key):
        b = result.baselines.get(key)
        return f"${b.margin:,.2f}" if b else "—"

    if SURROGATE_INFO is not None:
        model_note = (
            "Yield model: ETR surrogate (labels = the cited Stage-1 bridge); "
            "leave-crude-out honesty in models/model_card.md."
        )
    else:
        model_note = "Yield model: Stage-1 TBP bridge directly."
    budget_note = (
        f"{result.runtime_s:.1f}s — inside the {DE_BUDGET_S:.0f}s budget"
        if not result.over_budget
        else f"⚠️ {result.runtime_s:.1f}s — OVER the {DE_BUDGET_S:.0f}s budget"
    )

    lp_row = result.baselines.get("lp")
    lp_note = (
        "<div class='callout'><b>How to read:</b> "
        + (
            f"DE (${margin_de:,.2f}) lands {abs(margin_de - lp_row.margin):.2f} "
            "above the exact LP through the surrogate — the disclosed ~1% model "
            "error; on the bridge path DE ≡ LP to <$0.005. Either way the "
            "optimizer is honest: it never 'beats' the true optimum."
            if lp_row is not None and margin_de >= lp_row.margin
            else "DE meets the exact LP bar — the physics are linear, so matching it is the win."
        )
        + f" Uplift {uplift:+.1%} vs the equal-weight blend you set below the "
        "slider severity.</div>"
    )

    mo.Html(
        f"""
        <div class="card">
          <div class="sec" style="margin-top:0"><span class="idx">▶</span><div>
            <h2>Deep re-optimization — live result</h2>
            <p class="sub">Bridge yields · Brent costs · USGC prices · quality
            specs enforced (RON / RVP / freeze / cetane)</p>
          </div></div>
          <table>
            <tr><th>Crude</th><th>Blend share</th></tr>
            {rows}
          </table>
          <p style="font-family:var(--mono); font-size:14px">
            <b>FCC severity:</b> {sev:.2f} ·
            <b class="bar-de">DE margin: ${margin_de:,.2f}/bbl</b> ·
            <b>Uplift:</b> {uplift:+.1%} · <b>Constraints:</b> {status}
          </p>
          <table>
            <tr><th>Baseline (spec §3.4)</th><th>Margin $/bbl</th></tr>
            <tr class="bar-de"><td>DE optimum (this run)</td><td>{margin_de:,.2f}</td></tr>
            <tr><td>LP optimum — the honest bar</td><td>{_b("lp")}</td></tr>
            <tr><td>Random search (10k feasible draws)</td><td>{_b("random_search")}</td></tr>
            <tr><td>Equal-weight (at your slider severity)</td><td>{_b("equal_weight")}</td></tr>
          </table>
          {lp_note}
          <div class="legend">{model_note} · Runtime: {budget_note}.</div>
        </div>
        """
    )
    return


@app.cell
def _(PRICES, SURROGATE_INFO, mo):
    # 06 · Trust layer — collapsed by default; every number's provenance.
    if SURROGATE_INFO is not None:
        lco = SURROGATE_INFO["cv_leave_crude_out"]
        lco_note = (
            f"Leave-crude-out honesty: gasoline {lco['yield_gasoline']['r2']:.2f}, "
            f"diesel {lco['yield_diesel']['r2']:.2f}, jet "
            f"{lco['yield_jet']['r2']:.2f} (trees can't extrapolate below a "
            "held-out crude's range — quantified, not hidden), petrochem "
            f"{lco['yield_petrochem']['r2']:.2f}."
        )
    else:
        lco_note = "Surrogate metrics: models/model_card.md."

    mo.accordion(
        {
            "06 · A — Model & validation": mo.md(
                f"""
                - **Stage-1 bridge:** TBP cut-point integration + FCC conversion
                40→80% linear in severity (Gary & Handwerk cited ranges);
                ground-truthed to **±0.2 vol%** vs published cut tables.
                - **Surrogate:** ETR 150×14×4, dual CV — random 5-fold (headline)
                + leave-crude-out (honesty), always together. {lco_note}
                - **DE = LP to <$0.005/bbl:** the bridge is affine in severity, so
                the exact LP is the honest bar and DE meets it (methodology §6a).
                """
            ),
            "06 · B — Data provenance (real vs assumed)": mo.md(
                f"""
                - **REAL:** assays (TotalEnergies / ExxonMobil sheets, row 3);
                product prices — gasoline ${PRICES.get("gasoline", float("nan")):.2f} /
                diesel ${PRICES.get("diesel", float("nan")):.2f} / jet
                ${PRICES.get("jet", float("nan")):.2f}/bbl (EIA USGC 12-mo, row 2);
                Brent anchor $69.10/bbl (row 9).
                - **ASSUMED:** per-grade differentials (quality-rationale table in
                `data/costs.py`; refresh path: OPEC MOMR actuals).
                - **PLACEHOLDER:** petrochem pool price (no citable EIA spot for
                the LPG/propylene/residue basket — probed; documented).
                - Every constant cited in `docs/methodology.md` — nothing invented
                silently.
                """
            ),
            "06 · C — Reproduce everything": mo.md(
                """
                ```bash
                uv sync                                        # locked env (uv.lock committed)
                PYTHONUTF8=1 uv run pytest                     # 137 offline tests
                PYTHONUTF8=1 uv run python scripts/train_surrogate.py    # ~5 s, deterministic
                PYTHONUTF8=1 uv run python scripts/sensitivity_study.py  # 100 DE seeds
                PYTHONUTF8=1 uv run python scripts/run_scenarios.py      # 10k Monte Carlo
                ```
                All randomness is seeded (20260919 / 42); committed artifacts
                regenerate deterministically.
                """
            ),
        }
    )
    return


@app.cell
def _(mo):
    mo.Html(
        """
        <div class="foot">
          <b>Transparency:</b> methodology demo on public data — not Dangote's
          actual operations. Real: assays, EIA USGC prices, Brent anchor, FX/WTI
          context. Assumed/placeholder inputs disclosed in section 06 and in
          <a href="https://github.com/batestguy/dangote-refinery-optimizer/blob/main/docs/data_provenance.md" target="_blank">docs/data_provenance.md</a>
          · Repo: <a href="https://github.com/batestguy/dangote-refinery-optimizer" target="_blank">batestguy/dangote-refinery-optimizer</a>
          · <a class="deerflow" href="https://deerflow.tech" target="_blank">✦ interface by Deerflow</a>
          <div style="margin-top:9px">
            <b>Methodology &amp; why:</b> every number on this page is either
            integrated from a published curve, cited to a source, or labeled
            ASSUMED with a rationale — because an optimization you can't audit
            is just a claim. Full audit trail:
            <a href="https://github.com/batestguy/dangote-refinery-optimizer/blob/main/docs/methodology.md" target="_blank">docs/methodology.md</a>.
          </div>
          <div style="margin-top:6px; font-family:var(--mono)">Project by <b>JJMB</b> · 2026</div>
        </div>
        """
    )
    return


if __name__ == "__main__":
    app.run()
