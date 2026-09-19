# Dangote Refinery Blend Optimizer

[![CI](https://github.com/batestguy/dangote-refinery-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/batestguy/dangote-refinery-optimizer/actions/workflows/ci.yml)

ML surrogate (Extremely Randomized Trees) + differential evolution to optimize
the crude blend and FCC severity for a 650 kbpd refinery — maximizing margin
under blend, quality, and severity constraints, with full scenario risk
analysis. **Methodology demo on free/open data only.** Not affiliated with
Dangote; no proprietary data.

**Status: all modeling phases complete (0–5).** Remaining: Phase 6 (dashboard
polish + HF Spaces deploy) and Phase 7 (write-ups) per
[`plan-improvement-spec.md`](plan-improvement-spec.md) §5.

## What's real vs. placeholder (read this first)

Every layer is either real public data or a disclosed assumption — nothing is
silently invented. Full source-by-source verification:
[`docs/data_provenance.md`](docs/data_provenance.md).

| Layer | Status | Provenance |
|---|---|---|
| 5-crude slate (Bonny Light, Forcados, Qua Iboe, ANS, Thunder Horse) | ✅ real published assays (TotalEnergies / ExxonMobil sheets) | row 3 |
| Yield model — Stage-1 TBP bridge, ground-truthed to ±0.2 vol% | ✅ physics from published curves + cited ranges | row 3 + methodology §1–5 |
| ETR surrogate (learns the bridge; 5-fold R² 0.982, gate >0.90) | ✅ labels are bridge-generated, none claimed as plant data | row 7 (superseded — see methodology §7) |
| Crude costs — EIA Brent trailing-12m + per-grade differentials | ✅ real Brent; differentials **ASSUMED** with rationale (refresh: OPEC MOMR) | row 9 |
| Product prices — EIA USGC spot (gasoline/diesel/jet) | ✅ real; **petrochem pool = disclosed PLACEHOLDER** | row 2 |
| Quality specs — RON / RVP / freeze / cetane | ✅ published cut qualities; 4 values **ASSUMED** with rationale | methodology §3c |
| Optimization — DE + exact LP bar (DE ≡ LP to <$0.005/bbl) | ✅ linear-physics finding documented | methodology §6a |
| Scenario risk — 10k correlated draws, per-draw re-opt | ✅ real EIA co-moves (block bootstrap) | methodology §7b |

## Headline results

| Question | Answer |
|---|---|
| Optimal diet (base state) | ~100% Alaska North Slope at max severity — sour discount beats sweetening costs |
| Margin vs equal-weight blend | **+$15.67 vs $14.24/bbl (+10.0%)** — clears the spec's "impressive" gate (>10%) |
| Is DE actually finding the optimum? | Yes — matches the exact LP to <$0.005/bbl; the physics are linear in the decision vars (methodology §6a) |
| Surrogate fidelity | max \|Δyield\| ≈ 0.0007 vs the bridge inside the training envelope |
| Re-optimization value under shocks | **+$2.56/bbl mean, and it flips the stress tail from −$3.50 to +$1.42 CVaR(5%)** |
| Downside risk | VaR(5%) $6.25 / CVaR(5%) $1.42 / P(loss) 0.8% across 10k correlated scenarios |
| Runtime | DE 0.85 s (bridge) / ~3.4 s (surrogate) per run — 30–60 s budget has ~20× headroom |

Figures: `docs/assets/convergence.png`, `seed_sensitivity.png`,
`margin_fan.png`, `tornado_margin.png`.

## Quickstart (free tooling only)

```bash
uv sync                            # creates .venv from uv.lock
uv run pytest                      # 127 tests
uv run ruff check .                # lint
uv run marimo run app/app.py       # the app, locally
```

Data artifacts (`data/derived/*.parquet|json`, committed) make everything run
offline; the only network fetches are optional EIA refreshes (cache-first).
Regenerable artifacts:

```bash
PYTHONUTF8=1 uv run python scripts/train_surrogate.py    # ~5 s → models/etr_surrogate.pkl (gitignored) + model card
PYTHONUTF8=1 uv run python scripts/sensitivity_study.py  # 100 DE seeds → docs/assets/ + data/derived/
PYTHONUTF8=1 uv run python scripts/run_scenarios.py      # 10k Monte Carlo (~85 s) → figures + summary
```

## Repo map

```
src/dangote_opt/
  config.py              all locked constants (specs, penalties, DE budget)
  data/                  EIA v2 client · assay parsers · cost/price anchors · CrudeOilMix mapper
  features/              blend.py (linear rules) · bridge.py (TBP→yields, exact batch path)
                         quality.py (RON/RVP/freeze/cetane + exact batch mirror)
  models/                dataset.py (bridge-label sampler) · train_surrogate.py (ETR + dual CV)
  optimization/          objective.py · de_driver.py (vectorized DE) · baselines.py (exact LP)
                         scenarios.py (bootstrap Monte Carlo)
  viz/                   convergence.py (Phase 4 figures)
app/app.py               marimo app — real slate, real prices, all phases wired
scripts/                 build_slate · build_costs · build_prices · train_surrogate ·
                         sensitivity_study · run_scenarios
tests/                   127 offline tests — batch-path exactness pinned to machine precision
docs/                    problem statement · data provenance · methodology · setup steps
models/model_card.md     committed Phase 3 deliverable (dual-CV numbers + importances)
notebooks/00_free_tier_driver.py   Colab driver (optional)
```

## Documentation index

- [`docs/problem_statement.md`](docs/problem_statement.md) — formulation, locked decisions, success gates
- [`docs/methodology.md`](docs/methodology.md) — every number in the codebase, cited (the audit trail)
- [`docs/data_provenance.md`](docs/data_provenance.md) — source-by-source verification table
- [`docs/setup-steps.md`](docs/setup-steps.md) — phase-by-phase execution record (Phases 0–5)
- [`models/model_card.md`](models/model_card.md) — surrogate dual-CV results
- [`knowledge.md`](knowledge.md) — session handovers + hard-won gotchas (agent-oriented)
- [`plan-improvement-spec.md`](plan-improvement-spec.md) — governing spec (roadmap, decisions, risks)

## The problem in one line

`maximize  Σᵢ yieldᵢ(x, severity)·priceᵢ − Σⱼ xⱼ·costⱼ` subject to blend API/sulfur
windows, quality specs (RON, sulfur, cetane, freeze point, RVP), and severity
bounds — with the DE result always reported against equal-weight, random-search,
and LP baselines, plus 10k-scenario downside metrics. Details:
[`docs/problem_statement.md`](docs/problem_statement.md).

## License

MIT — see [LICENSE](LICENSE).
