# Changelog

All notable changes to this project. Format based on Keep a Changelog.

## [Unreleased]

### Fixed
- Colab driver notebook: consolidate cell definitions to satisfy marimo's
  single-definition rule (`MultipleDefinitionError` on `load_dataset`/`os`/
  `subprocess`) — caught by WSL headless test.
- marimo app: the result cell nested its `mo.md()` inside `if run.value:` so
  marimo rendered nothing after clicking Run (only a cell's last *top-level*
  expression is displayed). Rewritten with `mo.stop()`; the severity slider,
  previously unused, now sets the equal-weight baseline's severity (spec §3.4);
  uplift guards against a zero baseline.
- Colab driver: dropped the unconditional `pip install datasets` side effect;
  `datasets` is now a declared project dependency (streaming use only); probe
  cell now depends on the install cell so DAG order is guaranteed on Colab.
- `.gitignore`: removed the blanket `*.parquet` rule that contradicted the
  "commit small derived parquet" workflow (raw/processed dirs stay ignored).
- Docs: spec §1 F2/F8 and §2.4 updated for the marimo decision and the verified
  Electric Sheep schema; Phase 4 time compression recorded as open item 7;
  problem statement baseline aligned to spec ("default severity"); setup-steps
  step 6 marked done; data provenance clarifies CrudeOilMix's gap-filler role.

### Added
- Objective: quadratic penalty for API-window / sulfur-cap violations
  (`CONFIG.constraint_penalty`) — DE can no longer return an infeasible blend
  that out-scores a feasible one; `margin()` exposes the unpenalized value the
  app reports. Placeholder yield model is now blend-aware (API → light-product
  yield, sulfur → distillate loss) so the POC has a real cost-vs-yield trade-off
  instead of trivially buying the cheapest barrel. Tests cover both.
- `scripts/colab-wsl-test.sh`: replicates the Colab free-tier workflow on
  Linux/WSL (clone → venv → editable install → sanity → headless marimo →
  pytest) using a standalone project-local uv; no sudo, no system changes.
- Verified HF streaming probes (CrudeOilMix + Electric Sheep) from WSL;
  schema findings recorded in `docs/data_provenance.md`.

### Decided (documented)
- Storage: project stays on `D:\Dangote` (external USB, benchmarked 2.6–8×
  slower writes than C: SSD; cold reads ~39 MB/s — an earlier "reads equal"
  result was a RAM-cache artifact; uv cache on C:). GitHub is the sole git
  backup. See `knowledge.md`.

- Colab/Kaggle: optional convenience only (CPU-bound workloads run locally;
  free GPU quotas are useless to ETR). Driver remains Colab-ready.

## [0.1.0] — 2026-09-18

### Added
- Phase 0 scaffold: `src/dangote_opt/` package (config, blend math, margin objective + simplex repair, constraints; contract stubs for data/bridge/surrogate/DE).
- marimo app POC (`app/app.py`) — mock slate, DE optimize on click, equal-weight comparison, transparency footer; deploys to HF Spaces in Phase 6.
- marimo Colab driver notebook (`notebooks/00_free_tier_driver.py`) with streaming data probes.
- Tests for config invariants, blending rules, objective/repair/constraints.
- CI (GitHub Actions: uv sync → ruff → pytest), `uv`-managed environment with committed `uv.lock`.
- Docs: problem statement, data provenance skeleton, setup-steps execution record; governing spec `plan-improvement-spec.md`.
- MIT license, `.env.example`, gitignore rules (raw data / secrets / artifacts never committed).
