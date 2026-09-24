---
title: Dangote Refinery Optimizer — Portfolio
emoji: 🛢️
colorFrom: blue
colorTo: green
sdk: static
pinned: true
---

# Crude-Blend Optimization at Refinery Scale

**ML surrogate + differential evolution for crude-blend / FCC-severity
planning at a 650 kbpd refinery** — a methodology demonstration built entirely
on free, open data (published crude assays, EIA price series), with every
number traceable to a cited source or labeled as a documented assumption.

## Live artifacts

* 🛢️ **Interactive dashboard** — [run it from the repo](https://github.com/batestguy/dangote-refinery-optimizer#readme)
  (marimo app: `uv run marimo run app/app.py`): headline economics, live
  NGN/USD + WTI ticker, optimal diet, 10k-scenario risk, one-click deep
  re-optimization. (HF-hosted interactive Space pending — Docker Spaces now
  require PRO on free accounts.)
* 💻 **Source repo** — [batestguy/dangote-refinery-optimizer](https://github.com/batestguy/dangote-refinery-optimizer):
  137 offline tests, CI green, deterministic seeds, `uv.lock` reproducibility.

## Headline results (deterministic, seeded)

| Result | Value |
|---|---|
| Optimal diet (base economics) | ~100% Alaska North Slope @ max FCC severity |
| Blend margin | **$15.67/bbl** |
| Uplift vs equal-weight blend | **+11.3%** (100-seed sweep) |
| DE vs exact LP | **≡ within $0.005/bbl** — physics are linear in the decision vars |
| Surrogate 5-fold R² (min) | **0.982** (gate >0.90); jet leave-crude-out 0.11 disclosed |
| Re-optimization value under price shocks | **+$2.56/bbl** mean; flips the loss tail (CVaR5 −$3.50 → +$1.42) |
| Downside risk (10k scenarios) | VaR(5%) $6.25 · CVaR(5%) $1.42 · P(loss) 0.8% |
| DE runtime | 0.85 s bridge / 3.4 s surrogate (30–60 s budget) |

## Why it's credible

* **The honest-bar problem, solved structurally:** the assay→yield bridge is
  affine in severity, so an exact LP is the ceiling for any approach — and DE
  meets it to half a cent. No strawman baselines.
* **Dual cross-validation, always reported together:** random 5-fold
  (headline) + leave-crude-out (honesty). The jet extrapolation collapse is
  quantified and explained, not hidden.
* **Traceability rule:** every number is (a) integrated from a published
  curve, (b) cited, or (c) labeled ASSUMED/PLACEHOLDER with a rationale and a
  refresh path. `docs/methodology.md` is the audit trail.
* **Free-tier discipline:** GitHub Actions + HF Spaces + EIA API + streaming
  datasets — nothing paid, anywhere.

*License: MIT. Not affiliated with Dangote Industries; no proprietary data.*
