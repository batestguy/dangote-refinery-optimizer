# Project Knowledge

## What This Project Is
ML surrogate model (Extremely Randomized Trees) + Differential Evolution optimization for **Dangote Refinery (650,000 bpd)** crude-blend and process-configuration planning. Goal: maximize refinery margin (product value − crude cost) subject to blend/capacity/quality constraints.

- **Type:** Portfolio project (methodology demonstration) — NOT a real Dangote system, no proprietary/NDA data.
- **Source of truth for scope:** `idea.txt` (master project brief, v0.1 — problem formulation §3, data strategy §4, architecture §5, phase plan §6, open questions §9). Reference sections by number when discussing with the user.
- **Status:** Pre-code. Only `idea.txt` exists. Next step is Phase 0 (repo scaffold, requirements, problem statement).

## Planned Stack (Python 3.11+)
- **Data:** pandas, NumPy, PyArrow (Parquet); HuggingFace `datasets`, `requests`
- **ML:** scikit-learn (ETR primary), XGBoost/LightGBM (comparison); SHAP for explainability
- **Optimization:** SciPy `differential_evolution`
- **Viz/App:** Matplotlib, Plotly; **marimo** for both analysis notebooks and the deployed app (HF Spaces hosting — decided 2026-09-18, replacing Streamlit; Streamlit kept as documented fallback)
- **Test:** pytest | **Env:** venv + pinned `requirements.txt`

## Commands (planned — none exist yet)
```bash
uv sync                     # install deps (uv + pyproject.toml)
pytest                      # tests/
marimo edit app/app.py      # dev the app
marimo run app/app.py       # run app locally (same file deploys to HF Spaces)
```

## Key Data Sources
- `anon12-neurips-2026/CrudeOilMix` (HF, CC-BY-4.0) — 1.14M synthetic samples from real assays
- `electricsheepafrica/nigerian_oilgas_crude_pricing` + `africa-synth-energy-oilgas-refineries-nigeria` (HF, MIT — **synthetic**)
- EIA Open Data API v2 (requires free API key in `.env`)
- ExxonMobil / TotalEnergies public crude assays; FCCU dataset (mlforpse.com)

## Conventions & Gotchas
- **Transparency rule:** Electric Sheep Africa + CrudeOilMix data are synthetic — always frame outputs as methodology demo, never as real Dangote operations.
- **Scope guard (avoid creep):** 4 products (gasoline, diesel, jet, petrochem), ~5 crudes in slate, single time period. Stick to Phases 0–4 before extras.
- Linear blending assumed for API gravity and sulfur: `API_blend = Σ x_j·API_j`, `S_blend = Σ x_j·S_j`.
- Success targets: surrogate R² > 0.80 (viable) / 0.90 (impressive); margin gain > 5–15% vs baseline.
- Deployment: HF Space (marimo template) — sleeps after ~48 h idle, ~30–60 s cold start; app must render a pre-computed fallback instantly on load. Pin a patched marimo release (CVE-2026-39987 precedent); no file-upload/code-exec widgets in the public app.
- No real-time/trading system; no Aspen HYSYS-style rigorous simulation.
- Planned license: MIT; secrets via `.env` (EIA key), committed template as `.env.example`.
- Planned layout: `src/{data,features,models,optimization,visualization}`, `notebooks/01–05`, `app/`, `tests/`, `models/`, `data/{raw,processed}` (see idea.txt §5.3).
- Open decisions live in idea.txt §9 — move them to "Decided" as they're made.
