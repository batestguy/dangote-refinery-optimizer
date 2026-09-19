# Dangote Refinery Blend Optimizer

> **🚧 WIP** — Phase 0 (scaffold). See [`plan-improvement-spec.md`](plan-improvement-spec.md) for the governing spec and [`docs/setup-steps.md`](docs/setup-steps.md) for the execution record.

ML surrogate (Extremely Randomized Trees) + differential evolution to optimize the crude blend and FCC severity for a 650 kbpd refinery — maximizing margin under blend, capacity, and product-quality constraints. **Methodology demo on free/open data only.** Not affiliated with Dangote; no proprietary data.

[![CI](https://github.com/batestguy/dangote-refinery-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/batestguy/dangote-refinery-optimizer/actions/workflows/ci.yml)

## What's real vs. placeholder (read this first)

| Layer | Status |
|---|---|
| Blend math + margin objective + constraints | ✅ implemented & tested |
| DE optimization driver + baselines (equal-weight / random / LP) | 🔜 Phase 4 |
| Assay→yield bridge — Stage 1: TBP cut-points + cited FCC ranges, ground-truthed vs published cut yields | ✅ implemented (`docs/methodology.md`) |
| ETR surrogate, dual-CV validation (random + leave-crude-out) | ✅ Phase 3 — 5-fold R² ≥ 0.98 (gate >0.90), LCO honesty metric in `models/model_card.md` |
| App (marimo, deploys to HF Spaces) | ✅ POC on real slate + surrogate/bridge yields + real costs & product prices |
| Prices | ✅ EIA-anchored (USGC spot; petrochem disclosed placeholder) |

All synthetic/illustrative inputs are marked `*` in the app and disclosed in [`docs/data_provenance.md`](docs/data_provenance.md).

## Quickstart (free tooling only)

```bash
uv sync                      # creates .venv from uv.lock
uv run pytest                # run tests
uv run ruff check .          # lint
uv run marimo run app/app.py # the app, locally
```

Free-tier workflows: heavy data pulls *can* run on **Colab** (`notebooks/00_free_tier_driver.py`; optional — CPU-bound work runs fine locally), the app deploys to an **HF Space** (Phase 6), CI is **GitHub Actions**.

## The problem in one line

`maximize  Σᵢ yieldᵢ(x, severity)·priceᵢ − Σⱼ xⱼ·costⱼ` subject to blend API/sulfur windows, quality specs (RON, sulfur, cetane, freeze point, RVP), and severity bounds — with the DE result always reported against equal-weight, random-search, and LP baselines. Details: [`docs/problem_statement.md`](docs/problem_statement.md).

## Repo map

```
src/dangote_opt/   config · data (Phase 1) · features/blend+bridge · models (Phase 3) · optimization · viz
app/app.py         marimo app → HF Space (Phase 6)
notebooks/         marimo analysis notebooks (Colab-friendly)
docs/              problem statement · data provenance · setup steps · methodology (Phase 2)
tests/             pytest — the math is tested before the ML exists
```

## License

MIT — see [LICENSE](LICENSE).
