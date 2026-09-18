# Project Knowledge

## What This Project Is
ML surrogate model (Extremely Randomized Trees) + Differential Evolution optimization for **Dangote Refinery (650,000 bpd)** crude-blend and FCC-severity planning. Goal: maximize refinery margin (product value − crude cost) subject to blend/capacity/quality constraints.

- **Type:** Portfolio project (methodology demonstration) — NOT a real Dangote system, no proprietary/NDA data.
- **Status:** Phase 0 complete — repo scaffolded, committed, and public: https://github.com/batestguy/dangote-refinery-optimizer (CI green, 17 tests passing). Implemented: config, blend math, margin objective + simplex repair, marimo app POC (placeholder yield model). Stubs awaiting phases: data acquisition (P1), TBP→yields bridge (P2), ETR surrogate (P3), DE driver + baselines (P4), dashboard polish (P6).
- **Governing docs:** `plan-improvement-spec.md` (all locked decisions §4 — read before changing scope) + `docs/setup-steps.md` (execution record) + `docs/problem_statement.md` (formulation) + `docs/data_provenance.md` (verified sources).

## Stack (Python 3.12, uv-managed)
- **Data:** pandas, NumPy, PyArrow (Parquet); HuggingFace `datasets` (streaming only), requests
- **ML:** scikit-learn (ETR primary), XGBoost/LightGBM (comparison); SHAP (Phase 3)
- **Optimization:** SciPy `differential_evolution`
- **App/Notebooks:** **marimo** for both (decided 2026-09-18, replacing Streamlit/Jupyter; Streamlit = documented ≤2-day fallback since all logic lives in src/)
- **Test/Lint:** pytest + ruff | **Env:** uv + pyproject.toml, `uv.lock` committed

## Commands
```bash
uv sync                        # install deps (uv manages Python 3.12; system 3.14 not used)
uv run pytest                  # tests
uv run ruff check .            # lint (CI runs both)
uv run marimo run app/app.py   # app locally; same file deploys to HF Spaces
# Colab (free tier): notebooks/00_free_tier_driver.py — clone → pip install -e . → probes
```

## Key Data Sources
- `anon12-neurips-2026/CrudeOilMix` (HF, CC-BY-4.0) — verified: 1,141,933 simulator-generated blend samples from 9,061 real assays; **stream, never bulk-download**
- `electricsheepafrica/*` (HF, MIT — **synthetic**): pricing CSV is only 27 rows (useless for economics — EIA-anchored instead); refineries dataset used for Dangote metadata only
- EIA Open Data API v2 — free key in `.env` (see `.env.example`); cache pulls to `data/raw/` parquet
- Public assays (ExxonMobil/TotalEnergies/Equinor/NUPRC) for the 5-crude slate — Phase 1
- FCCU dataset (mlforpse.com) — yield-vs-severity *shape* calibration — Phase 2

## Conventions & Gotchas
- **Transparency rule:** synthetic/placeholder inputs are marked `*` in the app and labeled in `docs/data_provenance.md`; never present outputs as real Dangote operations.
- **Scope guard:** 4 products, 5 crudes, single period; decisions change via the spec, not ad-hoc.
- Linear blending for API/sulfur (implemented in `features/blend.py`); quality-spec LBIs (RON, cetane, RVP) come as Phase 2 constraints.
- Dual CV in Phase 3: random 5-fold (headline) + leave-crude-out GroupKFold (honesty) — always report both.
- Baseline contract: DE always reported vs equal-weight + random + LP (spec §3.4).
- **Windows gotchas:** uv picked a broken LibreOffice Python — fixed via `uv python install 3.12` + `.python-version`; console is cp1252 — prefix marimo CLI with `PYTHONUTF8=1` when output has emoji; use POSIX bash syntax.
- **Storage decision (user-locked 2026-09-18):** project stays on `D:\Dangote` even though D: is an external USB drive — benchmarked vs C: (Samsung SSD): seq-write 35 vs 295 MB/s (8.4×), small-file create 322 vs 848 files/s (2.6×). Reads ≈ equal. Accepted trade-off: installs/git/pytest writes are slower; data reads fine. uv cache is on C: (default `%LOCALAPPDATA%`), so only venv materialization hits D:. No D: backup — GitHub is the sole git backup; D: reserved for write-once data archives. Revisit if WSL/git operations feel painful.
- Deployment (Phase 6): HF Space via `marimo-team/marimo-app-template` fork; sleeps ~48 h → pre-computed fallback must render instantly; pin CVE-2026-39987-patched marimo; no upload/code-exec widgets.
- Free-tier discipline: GitHub Actions + HF Space + Colab + EIA key + streaming HF datasets — nothing paid, ledger in `docs/setup-steps.md`.
