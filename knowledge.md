# Project Knowledge

## Session Handover (2026-09-19b) — START HERE
- **Done this session (Phase 1 data layer, code + live verification):** EIA v2 client (`data/acquire.py`: cache-first parquet + sidecars in `data/raw/eia/`, pagination w/ hard stop, `units` never coerced, injectable transport; route contract verified against official v2 guide) · assay records (`data/assays.py`: provenance-required, quality rules enforced at construction, `validate_slate()` = unique ids + exactly 5) · CrudeOilMix mapper (`data/crudeoilmix.py`: word-segment matching in `mix_json`, unknown keys surfaced, reject frame, whole-crude stream filter) · `scripts/eia_smoke.py` = live verification once key lands → then pin confirmed series IDs in provenance row 2 · **57 offline tests, ruff clean.**
- **EIA live-verified 2026-09-19 (key registered → `.env`, smoke run green):** catalog pinned — `petroleum/pri/spt` (USGC spot: `EPMRU` gas / `EPD2DXL0` ULSD / `EPJK` jet, `RGC`/`PF4`, $/gal; `EPCWTI`/`EPCBRENT` also on route in $/bbl) · `petroleum/sum/snd` (`EPC0`+`YIR`+**`NUS`** — NOT `NUS-Z00`, it has 0 `YIR` rows) · `petroleum/move/impcus` (`EPC0`+`IM0`+`NUS-NNI` = Nigeria). `units` is NOT a valid `data[]` column (echoed per row). Real parquet + sidecars now in `data/raw/eia/`. ⚠️ SECURITY near-miss: key briefly pasted into committed `.env.example` — moved to gitignored `.env`, never staged/pushed. No Bonny Light spot on EIA → Brent anchor `EPCBRENT` + documented differential (provenance row 9).
- **Slate finalized (Phase 1 exit criterion met):** Bonny Light / Forcados (TotalEnergies sheets) + Qua Iboe / Alaska North Slope / Thunder Horse (ExxonMobil) — real published assays, validated, committed as `data/derived/slate_phase1.parquet` + sidecar. **Arab Light/Urals substituted — no open TBP assays exist** (ExxonMobil library checked; don't re-search). Parsers in `data/assay_parsers.py`; yield basis per crude in `notes` (TE=wt%, XOM=vol% grid — bridge must not mix). PDFs gitignored in `data/raw/assays/` (vendor docs, not redistributed). Assay validation now also enforces cumulative-yield monotonicity.
- **Phase 2 Stage-1 bridge DONE (2026-09-19c):** `features/bridge.py` — cut scheme <180/180-260/260-360/360-540/>540 °C; FCC conversion 40→80% of VGO linear in severity (Gary & Handwerk cited range), splits gas 50%/LCO 18%/gas+coke 32%; HT loss 1% on diesel (ICCT ex.17); curves stored **vol% uniform** (TE parser fixed: vol column, gas-in-curve simplification ≈2 vol% documented). **Ground-truthed:** parsed-curve cuts vs published Bonny Light table ±0.2 vol% (§5 of methodology.md). `docs/methodology.md` cites every constant; Maples correlations reviewed & rejected (not openly reproducible — don't re-litigate). Objective has `yield_model` hook = Phase 3 ETR signature; app now runs REAL slate + bridge yields (costs still placeholder). 73 tests.
- **Cost anchor DONE (2026-09-19d, provenance row 9 ✅):** `brent_spot` in the EIA catalog (product `EPCBRENT`, duoarea **`ZEU`** — NOT `RGC`, probed live; series `RBRTE`, native $/bbl). `data/costs.py`: delivered cost = trailing-12m EIA Brent (**$69.10/bbl**, 132 cached monthly rows) + per-grade differential — every differential **ASSUMED** w/ documented quality rationale; refresh via OPEC MOMR actuals (Phase 2+). Ordering sanity tested (premium ~ API within sulfur class; sour discounts); strict KeyError on unknown grade — never silently default. Committed `data/derived/costs_phase2.parquet` + sidecar (`scripts/build_costs.py`). App runs real slate + real costs (footer discloses ASSUMED differentials). Result with real economics: DE blends 47% Forcados + 52% ANS (sour discount vs sweetening trade-off) at $21.47/bbl vs $20.05 equal-weight. 82 tests. Product prices remain placeholder — wiring the EIA USGC series into the objective is the last Phase 2 economics item.
- **Next up (Phase 2 remainder):** quality-spec LBIs (RON/cetane/RVP constraints, spec §3.3) into the penalty block; wire EIA USGC product prices into the objective (replaces `CONFIG.default_prices`); then Stage-2 ETR (Phase 3).
- **Also open:** verify driver on *real* Colab (optional); FCC correlation set at Phase 2 kickoff (spec §8 item 2); Phase 4 buffer allocation at Phase 3 exit (§8 item 7).
- **Do not re-litigate:** marimo (not Streamlit), all-in on marimo notebooks, 5 crudes/4 products/single period, DE baselines incl. LP, dual CV, uv tooling, public repo, Colab optional-only, project stays on D:.

## Session Handover (2026-09-18, rev. 2026-09-19) — plan audit
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
