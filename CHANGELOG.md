# Changelog

All notable changes to this project. Format based on Keep a Changelog.

## [Unreleased]

### Fixed
- Colab driver notebook: consolidate cell definitions to satisfy marimo's
  single-definition rule (`MultipleDefinitionError` on `load_dataset`/`os`/
  `subprocess`) — caught by WSL headless test.

### Added
- `scripts/colab-wsl-test.sh`: replicates the Colab free-tier workflow on
  Linux/WSL (clone → venv → editable install → sanity → headless marimo →
  pytest) using a standalone project-local uv; no sudo, no system changes.
- Verified HF streaming probes (CrudeOilMix + Electric Sheep) from WSL;
  schema findings recorded in `docs/data_provenance.md`.

### Decided (documented)
- Storage: project stays on `D:\Dangote` (external USB, benchmarked 2.6–8×
  slower writes than C: SSD; reads equal; uv cache on C:). GitHub is the sole
  git backup; D: reserved for write-once data archives. See `knowledge.md`.
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
