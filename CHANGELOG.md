# Changelog

All notable changes to this project. Format based on Keep a Changelog.

## [0.1.0] — 2026-09-18

### Added
- Phase 0 scaffold: `src/dangote_opt/` package (config, blend math, margin objective + simplex repair, constraints; contract stubs for data/bridge/surrogate/DE).
- marimo app POC (`app/app.py`) — mock slate, DE optimize on click, equal-weight comparison, transparency footer; deploys to HF Spaces in Phase 6.
- marimo Colab driver notebook (`notebooks/00_free_tier_driver.py`) with streaming data probes.
- Tests for config invariants, blending rules, objective/repair/constraints.
- CI (GitHub Actions: uv sync → ruff → pytest), `uv`-managed environment with committed `uv.lock`.
- Docs: problem statement, data provenance skeleton, setup-steps execution record; governing spec `plan-improvement-spec.md`.
- MIT license, `.env.example`, gitignore rules (raw data / secrets / artifacts never committed).
