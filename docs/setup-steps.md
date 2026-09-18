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

## Step 6 — GitHub repo (public, per spec decision 17) ⏳
```
gh repo create dangote-refinery-optimizer --public --source . --push
```
- Creates repo under `batestguy`, sets remote `origin`, pushes `main`.
- README carries a WIP banner + CI badge so day-1 visitors see intent, not incompleteness.
**Accept:** `gh repo view` returns the repo; Actions tab shows the CI run passing on the first push.

## Step 7 — CI on GitHub Actions (free for public repos) ✅ (workflow committed; run verifies after push)
`.github/workflows/ci.yml`: checkout → setup-uv → Python 3.12 → `uv sync` → `ruff check` → `pytest`.
**Accept:** green check on `main` head commit.

## Step 8 — Colab free-tier workflow (usable from Phase 1) ✅ (driver committed)
Pattern: mount repo → `pip install -e .` (or `uv`-less plain pip) → run heavy data pulls in Colab → **commit only small derived parquet/CSV artifacts**, never raw dumps (repo stays light; raw data lives in Colab Drive or local `data/raw/`, which is gitignored).
The driver notebook also **streams** CrudeOilMix (HF datasets streaming) so we never download the full multi-GB benchmark.
**Accept:** `notebooks/00_free_tier_driver.py` runs top-to-bottom on a free Colab CPU session (verify in Phase 1 kickoff).

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
