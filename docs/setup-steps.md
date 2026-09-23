# Setup Steps — Logical Sequence (Phase 0)

> Execution record for the scaffold. Every step lists its acceptance criterion.
> Everything here is **free tier**: local tooling, GitHub public repo, GitHub Actions,
> HuggingFace Space (CPU), Colab (CPU), and all data sources from the provenance doc.

## Step 0 — Tooling check ✅
| Tool | Required | Found |
|------|----------|-------|
| git | any recent | 2.53.0 |
| uv | ≥0.4 | 0.11.28 |
| gh CLI (authenticated) | any | 2.93.0, account `batestguy` |
| python | 3.11+ target for project | 3.14.4 system (project pins ≥3.11; 3.12 resolved by uv) |

## Step 1 — Write documentation before code ✅
1. `docs/setup-steps.md` (this file) — the execution record.
2. `docs/problem_statement.md` — amended formulation (severity var, quality specs, 3-way baseline).
3. `docs/data_provenance.md` — source-by-source verification table.
4. `plan-improvement-spec.md` — already exists; governs all decisions.
**Accept:** docs exist and are referenced from README before any commit.

## Step 2 — Project scaffold ✅
1. `pyproject.toml` — project metadata, deps, `[dependency-groups] dev` (pytest, ruff), hatchling build, ruff+pytest config.
2. `src/dangote_opt/` — package layout per spec §5: `config`, `data/`, `features/`, `models/`, `optimization/`, `viz/`.
   - **Implemented now** (pure math, no data needed, fully testable): `features/blend.py` (linear blend properties), `optimization/objective.py` (margin function + simplex repair + constraint checks).
   - **Stubbed now** (raise `NotImplementedError` with docstring contracts): data acquisition, cut-point bridge, surrogate, DE driver — their turn comes in Phases 1–4.
3. `app/app.py` — marimo app (POC: mock slate + DE on click) — the file that later deploys to HF Spaces unchanged.
4. `notebooks/00_free_tier_driver.py` — marimo notebook that runs on **Colab free tier**: guarded installs, CrudeOilMix streaming probe (no full download), EIA key check.
5. `tests/` — pytest covering the implemented math + config invariants.
6. Repo files: `.gitignore`, `.env.example`, `LICENSE` (MIT), `README.md`, `CHANGELOG.md`.
**Accept:** `uv sync && ruff check . && pytest` all pass locally.

## Step 3 — Environment lock ✅
`uv sync` resolves and writes `uv.lock`. **`uv.lock` is committed** (reproducibility = free recruiter signal).
**Accept:** `uv.lock` exists; `uv run pytest` works without manual installs.

## Step 4 — Quality gates ✅
- `ruff check .` (lint) and `ruff format` (style) — same rules run in CI.
- `pytest` — all green before any commit.
**Accept:** zero lint errors, zero test failures.

## Step 5 — Local git history ✅
1. `git init -b main`
2. `.gitignore` excludes: `.env`, `data/raw/`, `data/processed/`, `models/*.pkl`, caches, `.venv`. (`uv.lock` NOT ignored.)
3. Single initial commit: `chore: scaffold phase 0 — src layout, marimo app, tests, CI, docs`.
**Accept:** `git status` clean after commit; no secrets staged.

## Step 6 — GitHub repo (public, per spec decision 17) ✅ (2026-09-18: https://github.com/batestguy/dangote-refinery-optimizer)
```
gh repo create dangote-refinery-optimizer --public --source . --push
```
- Creates repo under `batestguy`, sets remote `origin`, pushes `main`.
- README carries a WIP banner + CI badge so day-1 visitors see intent, not incompleteness.
**Accept:** `gh repo view` returns the repo; Actions tab shows the CI run passing on the first push.

## Step 7 — CI on GitHub Actions (free for public repos) ✅ (green on `main` after first push)
`.github/workflows/ci.yml`: checkout → setup-uv → Python 3.12 → `uv sync` → `ruff check` → `pytest`.
**Accept:** green check on `main` head commit.

## Step 8 — Colab free-tier workflow (usable from Phase 1) ✅ (driver committed)
Pattern: mount repo → `pip install -e .` (or `uv`-less plain pip) → run heavy data pulls in Colab → **commit only small derived parquet/CSV artifacts under `data/derived/`**, never raw dumps (repo stays light; raw data lives in Colab Drive or local `data/raw/`, which is gitignored — `.gitignore` deliberately has *no* blanket `*.parquet` rule so derived slices can be tracked).
The driver notebook also **streams** CrudeOilMix (HF datasets streaming) so we never download the full multi-GB benchmark.
**Accept:** `notebooks/00_free_tier_driver.py` runs top-to-bottom on a free Colab CPU session (verify in Phase 1 kickoff).

**WSL verification (2026-09-18):** `scripts/colab-wsl-test.sh` replicates the Colab
pattern on Linux (clone → venv → editable install → sanity → headless marimo check →
pytest): all green, 17/17 tests. Two verified findings recorded in
`docs/data_provenance.md`: (1) CrudeOilMix's assay detail is nested in `mix_json`;
(2) Electric Sheep pricing is an annual 1999–2025 per-grade series (Bonny Light,
Forcados, Qua Iboe, Brass River, Escravos + Brent spreads) — usable as a
labeled-synthetic crude-cost anchor; product prices still come from EIA. Note:
`marimo export script` validates structure but does not execute network probes —
run probe cells as a script to test connectivity.

## Step 8b — Phase 1 data layer (2026-09-19) ✅ (code + offline tests; live pulls pending EIA key)
- `src/dangote_opt/data/acquire.py`: EIA v2 client — cache-first parquet under
  `data/raw/eia/`, provenance sidecars, pagination guard, fake-transport tests.
- `src/dangote_opt/data/assays.py`: validated assay records (provenance-doc
  quality rules enforced at construction) + 5-crude slate validation.
- `src/dangote_opt/data/crudeoilmix.py`: `mix_json` mapper (tolerant key
  matching, reject tracking) + whole-crude streaming (no bulk download).
- `scripts/eia_smoke.py`: tiny live pull per catalog series once `EIA_API_KEY`
  is in `.env` — run it, then pin verified series IDs in `docs/data_provenance.md`.
**Accept:** `pytest` green offline (57 tests); live verification is the remaining
Phase 1 exit criterion for the EIA row.

## Step 8c — Five-crude slate (2026-09-19) ✅ (Phase 1 exit criterion)
- Vendor PDFs downloaded to `data/raw/assays/` (gitignored): Bonny Light +
  Forcados (TotalEnergies), Qua Iboe + Alaska North Slope + Thunder Horse
  (ExxonMobil).
- `src/dangote_opt/data/assay_parsers.py`: format-specific parsers →
  `AssayRecord`s (whole-crude API/sulfur + TBP curve, yield basis labeled).
- `scripts/build_slate.py` → `data/derived/slate_phase1.parquet` + sidecar
  (committed); all records pass `validate_slate()`.
- Arab Light/Urals substituted (no open assays) — documented in provenance row 3.
**Accept:** committed slate parquet validates; spot-checked API/S match vendor
sheets; CI green.

## Step 9 — Deployment path (Phase 6, not now)
1. Fork `huggingface.co/spaces/marimo-team/marimo-app-template` → new Space.
2. Copy `app/app.py` → `app.py` in the Space; list deps in Space `requirements.txt` (pinned versions from `uv.lock`).
3. Auto-deploy on commit. Verify cold-start fallback renders (spec §3.7).
4. Pin the CVE-2026-39987-patched marimo release at this point (spec open item 5).
**Accept:** public Space URL renders pre-computed fallback in <2 s.

## Free-tier ledger (nothing above has a paid component)
| Resource | Tier | Limit we design around |
|----------|------|------------------------|
| GitHub repo + Actions | Free (public) | 2,000 CI min/mo (we use ~2/run) |
| HF Space (Phase 6) | Free CPU | sleeps ~48 h; ~30–60 s cold start |
| Colab (Phase 1+) | Free CPU | ~12 h sessions; use Drive for raw data |
| EIA API | Free key | 5,000 req/h (cache to parquet) |
| HF datasets streaming | Free | no bulk download needed for probe |
| open.er-api.com FX | Free | fair use; cache 1 h |

---

# Phase 2–5 execution record (2026-09-19 sessions)

Continuation of the Phase 0 record above. Each section = one merged phase with
its acceptance criteria and the honest findings encountered.

## Step 10 — Phase 1: data layer live ✅ (2026-09-19)
- EIA key registered → `.env` (gitignored); `scripts/eia_smoke.py` green.
- Catalog pinned live (provenance row 2): `petroleum/pri/spt` USGC spot
  (EPMRU/EPD2DXL0/EPJK), `petroleum/sum/snd` refinery inputs, `petroleum/move/impcus`
  Nigeria imports; Brent added later on the same route (row 9, duoarea `ZEU`).
- Security near-miss recorded: key briefly pasted into `.env.example` — moved to
  `.env` before any commit. Check staged files when touching env docs.
**Accept:** live pulls cached with sidecars; row 2 ✅.

## Step 11 — Phase 2a: five-crude slate ✅ (2026-09-19, commit `710f6e2`)
- Parsers for two vendor formats (TE interleaved half-tables wt%; XOM 10 °C vol%
  grid) → validated `AssayRecord`s → `data/derived/slate_phase1.parquet` + sidecar.
- Arab Light / Urals substituted (no open TBP assays) per spec §8 item 1.
- Physical-invariant validator (cumulative yield non-decreasing in T) caught a
  real parser bug — junk from cut-property sections. Keep invariants in validators.
**Accept:** slate validates; ground-truth vs published cut tables ±0.2 vol% (later §5).

## Step 12 — Phase 2b: Stage-1 bridge ✅ (2026-09-19, commit `a805e4f`)
- `features/bridge.py`: TBP cut-point integration; FCC conversion 40→80% of VGO
  linear in severity (Gary & Handwerk cited); HT loss 1% (ICCT ex. 17); curves
  stored vol%-uniform.
- Maples FCC correlations rejected for traceability (coefficient tables not
  openly reproducible) — do not re-litigate.
- Ground truth: parsed-curve cuts vs published Bonny Light cut yields ±0.2 vol%;
  the one gap (low-naphtha cut) explained physically (~2.1 vol% dissolved C2–C4
  in the TBP's first row, quantified from the sheet's gas composition).
**Accept:** methodology.md cites every constant; objective gains `yield_model` hook.

## Step 13 — Phase 2c: cost anchor ✅ (2026-09-19, commits `378dea6`+`10b7a4a`)
- `brent_spot` live-verified (duoarea **`ZEU`** — the `RGC` guess probed empty:
  0-row cache is valid API behavior, noted).
- `data/costs.py`: delivered cost = trailing-12m Brent ($69.10) + per-grade
  differential (every value ASSUMED with quality rationale; strict KeyError on
  unknown grade). Result with real economics: DE picks 47% Forcados + 52% ANS.
- CI caught an F841 my local `tail -1` had masked — lesson: check exit codes,
  never the last line of piped output.
**Accept:** row 9 ✅; artifact + sidecar committed; app runs real costs.

## Step 14 — Phase 2d: quality specs + real product prices ✅ (2026-09-19, `0577952`)
- `features/quality.py`: RON (linear-by-volume), RVP (psi^1.25 index, Haverly),
  jet freeze, diesel cetane — from the bridge's component streams (one mass
  balance, `component_volumes()`), enforced via `quality_model` hook.
- Bridge gains octane units (isom/reform/alkylate/butane pull) — required, or
  RON 91 is infeasible by construction (SR naphtha blends at RON ≈ 58).
- XOM's RON row unusable in PDF extraction (MON > RON under every alignment) —
  labeled ASSUMED; freeze/cetane cross-check cleanly vs TE.
- Product prices: EIA USGC 12-mo averages ($84.77/$93.49/$88.94); petrochem stays
  disclosed PLACEHOLDER (probed `pri/resid`, `pri/refoth`, naphtha codes — no
  citable series).
- Proof the constraints have teeth: DE lands ~98% ANS with RON 91.4 / cetane 45.1
  both nearly binding.
**Accept:** Phase 2 complete; 102 tests; all docs updated.

## Step 15 — Phase 3: ETR surrogate ✅ (2026-09-19, `710f6e2`→`0577952` lineage, final push CI `35426502472`)
- `models/dataset.py`: 4,000 Dirichlet(α=0.55) × U(0,1) severity rows; features =
  blend-weighted properties + blend-weighted TBP cuts (the bridge's inputs).
- `models/train_surrogate.py`: ETR 150×14×4 (300 trees = 96.5 MB pkl, violates
  the 50 MB hosting guard — don't re-tune); dual CV per spec §3.5; self-written
  permutation importance (sklearn's scorer chokes on multi-output).
- Results (`models/model_card.md`, committed): 5-fold min R² **0.982** (gate
  passed); LCO — gasoline 0.93 / diesel 0.78 / petrochem 0.97, **jet 0.11**
  (honesty finding: the ANS fold tests below the training range; trees can't
  extrapolate; deployment never needs unseen crudes).
- Provenance row 7 superseded honestly: the MIT ML-PSE FCCU dataset is
  fault-detection data (no severity sweep) — confirmed via the repo's
  `dynamic.m`/`Plotall.m` — so the bridge's cited severity shape stands.
- DE hot-path lesson: per-call DataFrame + threadpool in `predict` made the app
  smoke time out (300 s); numpy rows + `n_jobs=1` inside DE fixed it.
**Accept:** both CV protocols reported; pkl gitignored + deterministic; 114 tests.

## Step 16 — Phase 4: optimization driver + baselines ✅ (CI `35429004230`)
- Exact batch paths: `bridge.blend_yields_batch` + `quality.BatchQualityModel`
  (affine-in-severity decomposition) — row-wise ≡ scalar paths at machine
  precision (pinned in `tests/test_phase4.py`). scipy vectorized DE passes
  populations **(n_vars, S)** — `batch_call` normalizes axes.
- `optimization/baselines.py`: equal-weight · random search (10k feasible draws,
  batched) · **exact LP** — `u_j = s·x_j` linearizes the affine physics; quality
  specs are hard linear constraints from the same coefficients as the DE penalty.
- Structural finding: **DE ≡ LP to <$0.005/bbl** — the physics are linear in the
  decision variables (methodology §6a). The honest bar (problem statement §4) is
  met exactly, mechanism documented. ⚠️ Don't double-square the quality
  violation — `violation_magnitude` already applies the LQ form once.
- Speed: **0.85 s (bridge) / ~3.4 s (ETR) per DE run — was ~127 s scalar.**
- 100-seed sweep committed (`data/derived/sensitivity_phase4.json`, mean
  $15.84 ± 0.00, uplift +11.3% through the surrogate) + convergence/histogram
  figures in `docs/assets/`.
- Buffer-week decision (spec §8 item 7): buffer goes to Phase 4 hardening +
  Phase 5 head start; full Monte Carlo chosen over the 3-scenario fallback.
**Accept:** 3-way baseline table in the app; runtime disclosed; 121 tests.

## Step 17 — Phase 5: scenario analysis ✅ (CI `35432368256`)
- `optimization/scenarios.py`: historical **block bootstrap** (blocks of 12
  consecutive months of EIA Δlog Brent+USGC, 2015–2025) — the brief's open
  questions answered with data: distribution = bootstrap; correlated shocks =
  inherited from real co-moves; FX/demand = documented out-of-scope (USD
  single-period price-taker, spec §7).
- Per-draw **LP re-solve** on the Phase 4 skeleton (`build_lp_problem`/`solve_lp`
  refactor — constraints price-independent; ~8.5 ms/draw; 10k in 85 s).
- ⚠️ Brent linkage: additive Δ = Brent_ref·(f−1) **cancels from the LP argmax**
  (Σx = 1) — subtract from margins, never add to LP costs; differentials preserved.
- ⚠️ Cache lookup: sidecar-located (`acquire.load_cached_series`) — cache-key
  reconstruction drifts when fetch params change.
- Results (`data/derived/scenarios_phase5.json`, seed 20260919): mean $17.68
  ± 8.29, **VaR(5%) $6.25 / CVaR(5%) $1.42 / P(loss) 0.8%**; fixed-blend CVaR(5%)
  **−$3.50** → re-optimization worth **+$2.56/bbl** and converts the tail
  positive. Two-regime diet: ANS 50.5% / Forcados 47.9% of draws.
- Fan + tornado figures in `docs/assets/`; app renders the precomputed summary
  (HF cold-start-safe; underscore-imports for marimo cell collisions).
**Accept:** 10k iterations with per-scenario re-optimization; VaR/CVaR/tornado
delivered; 127 tests; CI green.

## Step 18 — Phase 6 (in progress — item 1 done 2026-09-23)
1. ✅ (2026-09-23) CVE-2026-39987-patched marimo floor pinned in `pyproject.toml`:
   `marimo>=0.23.0` (vulnerability = pre-auth RCE via terminal WebSocket,
   fixed in 0.23.0); `uv.lock` carries 0.24.2 — no lock churn. CI gates green
   locally (127 tests, ruff, `marimo check`).
2. HF Space: fork the marimo template → copy `app/app.py` → pinned
   `requirements.txt` from `uv.lock` → verify cold start renders precomputed
   content <2 s. **Requires user's HF account.**
   — prep done 2026-09-23: `deploy/` kit has the Space `requirements.txt`
   (exact `uv.lock` versions) + the verbatim template Dockerfile + the deploy
   checklist (`deploy/README.md`). Remaining actions are user-side (create the
   Space, push the assembled root, watch the cold-start gate).
3. ✅ (2026-09-23) Live ticker (provenance row 8): NGN/USD FX (open.er-api.com,
   cache 1 h) + WTI spot (EIA daily `EPCWTI`/`YCUOK`, probed live) shipped in
   `data/ticker.py` + app cell; snapshot fallback
   `data/derived/ticker_latest.json` committed; 10 new tests (137 total).
4. HF Static Space portfolio page linking to the app.

## Free-tier ledger (nothing above has a paid component)
| Resource | Tier | Limit we design around |
|----------|------|------------------------|
| GitHub repo + Actions | Free (public) | 2,000 CI min/mo (~2/run used) |
| HF Space (Step 18) | Free CPU | sleeps ~48 h; cold start covered by precomputed cells |
| Colab | Free CPU | optional; everything runs locally |
| EIA API | Free key | 5,000 req/h (cache-first parquet) |
| HF datasets streaming | Free | no bulk download |
| open.er-api.com FX (Step 18 ✅) | Free | fair use; cache 1 h |
