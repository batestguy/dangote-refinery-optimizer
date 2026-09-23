---
title: Dangote Blend Optimizer
emoji: 🛢️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Dangote Refinery Blend Optimizer

Crude-blend + FCC-severity optimization at refinery scale — 5 real published
crude assays, a cited TBP cut-point bridge to 4 product pools, quality specs
with real teeth, and a differential-evolution optimizer benchmarked against an
exact LP. Live NGN/USD FX + WTI ticker; 10k-scenario risk analysis precomputed
and rendered instantly (the Space sleeps after ~48 h — cold start shows the
full static story in seconds; the deep re-opt takes ~1 s on the bridge path).

**Headline (deterministic, seeded):** $15.67/bbl base margin · +11.3% uplift
vs equal-weight · DE = LP to <$0.005/bbl · re-optimization worth +$2.56/bbl
under price shocks · VaR(5%) $6.25 / CVaR(5%) $1.42 / P(loss) 0.8%.

*Methodology demo on free/open data — no proprietary or NDA data, no claims
about Dangote's actual operations. Provenance for every number:
[`docs/methodology.md`](https://github.com/batestguy/dangote-refinery-optimizer/blob/main/docs/methodology.md)
in the [source repo](https://github.com/batestguy/dangote-refinery-optimizer).*
