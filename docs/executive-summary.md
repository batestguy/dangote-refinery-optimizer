# Executive Summary — Crude-Blend Optimization at Refinery Scale

**Project:** ML surrogate + differential evolution for crude-blend / FCC-severity planning (650 kbpd reference refinery)
**Status:** Phases 0–6 complete; methodology demo on free/open data
**Repo:** github.com/batestguy/dangote-refinery-optimizer · CI green · 137 offline tests

---

## The answer first

For a 650 kbpd refinery buying from a 5-crude slate (Bonny Light, Forcados,
Qua Iboe, Alaska North Slope, Thunder Horse) under real published assays and
EIA-anchored economics, the margin-maximizing policy is **concentrate the diet
on the best value crude and run the FCC at maximum severity** — here, ~100%
Alaska North Slope at severity 1.0, worth **$15.67/bbl**, a **+11.3% uplift**
over an equal-weight blend. Under 10,000 correlated price scenarios built from
real EIA monthly co-moves, **re-optimizing the blend as prices move is worth
+$2.56/bbl on average and converts the loss tail positive** (CVaR(5%)
−$3.50 → +$1.42). Downside risk is modest: VaR(5%) $6.25, P(loss) 0.8%.

The structural finding matters as much as the numbers: **differential
evolution matches an exact linear-program optimum to within half a cent.**
The assay→yield physics are linear in the decision variables (blend shares ×
severity), so the LP is the honest ceiling for *any* method — and DE meets it.
The project therefore demonstrates optimizer correctness rather than hoping
for a nonlinear free lunch that a 5-crude slate cannot offer.

## How the numbers are trustworthy

* **Real inputs, cited chain.** Five published vendor assays (TotalEnergies,
  ExxonMobil) feed a TBP cut-point bridge ground-truthed to ±0.2 vol% against
  published cut tables; product prices are EIA USGC spot series; the crude
  cost anchor is EIA Brent. Every assumption (per-grade differentials,
  petrochem pool price) is labeled ASSUMED/PLACEHOLDER with a rationale and a
  refresh path — `docs/methodology.md` is the audit trail.
* **Quality specs have real teeth.** Gasoline RON, RVP, freeze point and
  cetane enter as constraints from a component-level blending model; the base
  optimum runs with RON and cetane nearly binding, so the diet choice is
  doing real work, not dodging vacuous constraints.
* **Dual cross-validation, always together.** The ETR surrogate (150×14×4)
  posts random 5-fold R² ≥ 0.982 *and* a quantified leave-crude-out honesty
  finding: jet R² collapses to 0.11 when a crude's range is extrapolated
  below — disclosed because deployment never requires unseen crudes.
* **Deterministic and reproducible.** Seeded data generation (20260919),
  100-seed sensitivity sweep (margin σ = $0.0015), committed artifacts, and
  137 offline tests pinning mass balances, batch-path exactness, and VaR/CVaR
  relations.

## Risk framing for a planner

| Question | Answer from the scenario engine |
|---|---|
| What if prices move? | Bootstrap of real EIA co-moves (12-month blocks, 2015–2025) — correlated shocks, not independent noise |
| Is re-optimizing worth the trouble? | +$2.56/bbl mean; it is a risk lever, not just a profit lever |
| How bad can it get? | VaR(5%) $6.25; only 0.8% of scenarios lose money |
| Which crudes matter? | Two-regime diet: ANS optimal in 50% of scenarios, Forcados 48% |

## What this is not (deliberate scope)

No proprietary or NDA data; no claims about Dangote's actual operations; no
unit-level temperature/catalyst tuning (needs plant data); no FX or demand
channel (USD price-taker, single period); the petrochem pool price is a
disclosed placeholder pending a citable open series.

## The one-paragraph version

Built a refinery-scale crude-blend optimizer end to end on open data: parsed
published assays into a validated slate, built a cited TBP cut-point bridge to
product pools with quality-spec constraints, trained an ETR surrogate with
honest dual-CV reporting, drove it with differential evolution benchmarked
against an exact LP (they agree to half a cent), quantified downside risk with
a 10k-draw bootstrap Monte Carlo where every draw re-optimizes, and shipped it
as a cold-start-safe dashboard on free-tier infrastructure — 137 offline tests,
CI on every push, and provenance for every number.
