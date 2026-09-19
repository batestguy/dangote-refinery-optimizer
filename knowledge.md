# Project Knowledge

## Session Handover (2026-09-18, rev. 2026-09-19) — START HERE
- **Done this session (plan-vs-repo audit + fixes):** app bug fixed — the result cell rendered *nothing* after Run because `mo.md()` sat inside `if run.value:` (marimo only displays a cell's last top-level expression); rewritten with `mo.stop()`, severity slider now drives the equal-weight baseline severity (spec §3.4) · constraint handling added to `RefineryObjective.__call__`: linear+quadratic penalty (`CONFIG.constraint_penalty = 10_000`) for API-window/sulfur-cap violations, plus `margin()` (unpenalized, what the app reports) / `violation_magnitude()` / `blend_properties()` (reuses features/blend.py) · placeholder yields now **blend-aware** (API→light products, S→distillate loss) so DE has a real trade-off — it still picks 100% Urals\* on the mock slate, but legitimately ($7.04 vs $1.15 eq-weight; margins are illustrative until Phase 2) · `datasets` declared dep, driver no longer pip-installs, probe cell ordered after install via DAG dep · `.gitignore` blanket `*.parquet` removed (derived slices go in `data/derived/`) · spec F2/F8/§2.4 annotated for the marimo decision + verified Electric Sheep schema; Phase 4 one-week-vs-scope compression logged as **open item 7** · **22 tests, commit 5f4c25c pushed, CI green** (run 35413685351).
- **Next up (Phase 1, in order):** ① register EIA API key → `.env` (**user action, only blocker**) · ② implement `src/dangote_opt/data/acquire.py` (EIA client w/ parquet caching, assay parsers) · ③ write `mix_json` schema mapper for CrudeOilMix · ④ finalize 5-crude slate from public assays (spec §8 item 1).
- **Also open:** verify driver on *real* Colab (optional — WSL test already covers the pattern); FCC correlation set choice at Phase 2 kickoff (spec §8 item 2); Phase 4 buffer allocation at Phase 3 exit (spec §8 item 7).
- **Do not re-litigate:** marimo (not Streamlit), all-in on marimo notebooks, 5 crudes/4 products/single period, DE baselines incl. LP, dual CV, uv tooling, public repo, Colab optional-only, project stays on D:.

## What This Project Is
ML surrogate model (Extremely Randomized Trees) + Differential Evolution optimization for **Dangote Refinery (650,000 bpd)** crude-blend and FCC-severity planning. Goal: maximize refinery margin (product value − crude cost) subject to blend/capacity/quality constraints.

- **Type:** Portfolio project (methodology demonstration) — NOT a real Dangote system, no proprietary/NDA data.
- **Status:** Phase 0 complete — repo scaffolded, committed, and public: https://github.com/batestguy/dangote-refinery-optimizer (CI green, 22 tests passing). Implemented: config, blend math, margin objective + simplex repair + constraint penalty, blend-aware placeholder yield model, marimo app POC. Stubs awaiting phases: data acquisition (P1), TBP→yields bridge (P2), ETR surrogate (P3), DE driver + baselines (P4), dashboard polish (P6).
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
- **marimo gotchas:** a cell renders only its last *top-level* expression — a `mo.md()` inside `if ...:` shows nothing; use `mo.stop(cond, fallback_output)` then end the cell with the output (this bug shipped in the Phase 0 app and was fixed 2026-09-19). Source order ≠ execution order: a cell that needs another's side effect (e.g. Colab install) must reference one of its variables. `datasets` is a declared dependency — never `pip install` from a notebook.
- **Windows gotchas:** uv picked a broken LibreOffice Python — fixed via `uv python install 3.12` + `.python-version`; console is cp1252 — prefix marimo CLI with `PYTHONUTF8=1` when output has emoji; use POSIX bash syntax.
- **Git artifacts rule:** `data/raw/` and `data/processed/` are gitignored; small derived slices go under `data/derived/` and ARE committed (no blanket `*.parquet` ignore).
- **Storage decision (user-locked 2026-09-18, verified same day):** project stays on `D:\Dangote`. Verified facts: D: is a USB external drive ("Generic External USB Device") — NOT an SSD (cold-file read 39 MB/s on a file untouched since Mar 2025; write 35 MB/s; small-file create 322/s; the only SSD is C:'s Samsung MZNLN256HAJQ). USB enclosures hide the media flag, so identity queries are inconclusive — trust the cold-read benchmark. Earlier "reads ≈ equal" claim was RAM-cache artifact, now corrected. Accepted trade-off: cold reads + installs + git commits are slow; mitigate by keeping working parquet slices small. uv cache is on C: (default `%LOCALAPPDATA%`). No D: backup — GitHub is the sole git backup. C: migration offer stands (~10 min) if this ever hurts.
- Deployment (Phase 6): HF Space via `marimo-team/marimo-app-template` fork; sleeps ~48 h → pre-computed fallback must render instantly; pin CVE-2026-39987-patched marimo; no upload/code-exec widgets.
- Free-tier discipline: GitHub Actions + HF Space + Colab + EIA key + streaming HF datasets — nothing paid, ledger in `docs/setup-steps.md`.
