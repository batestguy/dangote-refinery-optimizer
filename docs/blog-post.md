# The honest optimizer: building a refinery blend planner where DE matches the LP to half a cent

*How a methodology project answered the question most optimization portfolios
dodge: is the fancy optimizer actually earning its keep?*

---

## The project in one sentence

I built a **crude-blend and FCC-severity optimizer for a 650,000 barrel-per-day
refinery** — end to end, on nothing but free and open data — and shipped it as
an interactive dashboard: you press a button, a differential-evolution solver
re-optimizes the refinery's crude diet in about a second, and every number on
the page can show you its provenance.

This post is about the finding I didn't expect to be the headline: the
meta-optimizer and the boring optimizer agree to **half a cent per barrel** —
and why that is the most credible result in the whole project.

## The problem

A refinery buys crude and sells products. Buy the wrong crudes, or run the
FCC unit at the wrong severity, and you bleed money on every barrel. The
planning question is: given a slate of crudes with published assay data
(API gravity, sulfur, a full TBP distillation curve), product prices, and
quality specs (gasoline must hit RON 91, diesel must hit cetane 45, and so
on) — **what blend and what severity maximize margin per barrel?**

The formulation is clean: 6 continuous decision variables (5 blend shares that
sum to 1, plus an FCC severity in [0, 1]), a margin objective, and a
constraint block. What's *not* clean is the middle: crude assays don't
contain yields. Assays describe feed; yields come from process units. There
is no public dataset that joins them. That missing join is where most
"AI optimizes the refinery" projects quietly die, because the honest options
are unglamorous: build the refinery's response surface yourself from cited
engineering correlations, or invent numbers and hope no domain reviewer
looks closely.

I built the bridge. Every crude's TBP curve is integrated into cut fractions
(naphtha, middle distillate, VGO, residue), FCC conversion rises linearly
with severity over a range cited from Gary & Handwerk's classic textbook, and
the product pools come out the other side with qualities blended by the
standard industry mixing rules. The bridge was then ground-truthed against a
published cut table for Bonny Light: **±0.2 vol% on every cut**. Not
neural, not novel — but *defensible*, which is worth more.

## The trap this project refuses

Here is the standard playbook for ML-optimization portfolios: train a
surrogate, run a metaheuristic, report "X% improvement over baseline," where
the baseline is something conveniently weak. A technical interviewer who has
seen a hundred of these will ask one question: **"What's the LP bound?"**

Because if your physics are linear in the decision variables, a linear
program finds the *true* optimum, and any fancy optimizer is only interesting
if it beats it — or matches it faster, or handles constraints the LP can't.

So I built the exact LP as a mandatory baseline. The substitution is almost
disappointingly simple: severity enters the bridge linearly, so writing
`u_j = s · x_j` (severity share of each crude) linearizes the whole problem —
the same quality-spec coefficients that penalize the DE become hard
constraints, and `scipy.optimize.linprog` solves it in milliseconds.

Result: **differential evolution matches the LP to within $0.005/bbl.**

| Method | Margin ($/bbl) |
|---|---|
| Equal-weight blend (the intuitive default) | 14.23 |
| Random search (10k feasible draws) | 15.62 |
| **Exact LP (the honest bar)** | **15.67** |
| Differential evolution | 15.67 (Δ < $0.005) |

Is that a failure? It's the opposite. It means the optimizer is *correct*.
It means the reported uplift (+11.3% over equal-weight) is real and
structural — better crude selection and severity, not noise — and it means
nobody can sink the project by running the LP themselves. When the physics
had been linear, claiming a nonlinear edge would have been the actual
failure. The mechanism is documented in the methodology (§6a): with a
5-crude slate and an affine bridge, there is no nonlinear landscape to
exploit, and saying so plainly is worth more than a fabricated one.

## Where the ML actually earns its keep

If the LP is exact, why a surrogate at all? Two reasons, both honest ones.

First, speed: the surrogate (an Extremely Randomized Trees ensemble, 150×14×4
— sized to stay under 50 MB after discovering 300 trees costs 96.5 MB) cuts
the DE round-trip from 0.85 s to ~3.4 s *including* feature construction, and
it matters for the one place latency is real: a cold dashboard visitor.

Second, and more important, the surrogate is where the project's **honesty
metric** lives. Cross-validation for a blend model has a subtle trap:
samples from the same crude are correlated, so random k-fold inflates R².
The protocol therefore always reports *two* numbers:

* **Random 5-fold:** R² ≥ 0.982 on every product — the headline, and it
  passes the >0.90 gate.
* **Leave-one-crude-out:** the model has never seen that crude at all.
  Gasoline holds at 0.93, petrochem at 0.97, diesel drops to 0.78 — and jet
  **collapses to 0.11**.

That jet number is my favorite result in the project. The held-out crude's
jet yield sat below the training range, and tree ensembles cannot
extrapolate — so the model fails *exactly where theory says it must*, in a
way that is quantified, explained in the model card, and irrelevant in
deployment (the optimizer only ever searches the trained envelope). An
interviewer who spots the leakage risk will find it already disclosed, with
the mechanism, in the docs. That's the difference between a portfolio and a
demo.

## Risk: the part planning actually cares about

A single optimum is a point estimate; a planner needs a distribution. The
scenario engine bootstraps **12-month blocks of real EIA monthly price
moves** (Brent + USGC products, 2015–2025) — preserving the correlation
between crude and product shocks that independent sampling would destroy —
and re-solves the LP for all 10,000 draws (about 85 seconds, because the
batch paths are vectorized).

Three findings:

1. **Re-optimization is a risk lever, not just a profit lever.** The fixed
   blend loses money in the tail (CVaR(5%) = −$3.50/bbl). Re-optimizing per
   scenario flips that tail positive (+$1.42) *and* adds +$2.56/bbl on
   average. The flexibility is worth more than the level.
2. **Downside is bounded.** VaR(5%) is $6.25 below the mean; only 0.8% of
   scenarios lose money at all.
3. **The diet is two-regime.** Across 10k price worlds, the optimal blend is
   Alaska North Slope ~50% of the time and Forcados ~48% — the sour-crude
   discount versus the cost of sweetening it upstream is the central
   economic trade-off, and it genuinely switches with prices.

## What shipping looked like

The dashboard is a marimo notebook — reactive cells, pure Python, Git-diffable
— deployed as a Docker Space on Hugging Face's free tier. The constraint that
shaped it: the Space sleeps after ~48 hours, and a recruiter's first visit
should not start with a 30-second spinner. So the entire static story —
headline economics, live FX/WTI ticker with staleness badges, the optimal
diet, the risk analysis — renders from committed artifacts in under two
seconds, and only the deep re-optimization waits for a click.

Everything is free-tier: GitHub Actions CI (137 offline tests, every push),
the EIA API, HF Spaces, streaming dataset access. The assembly script for the
Space root runs safety assertions before it will build — no `.env` (API keys),
no model artifacts, dependency pins verified against the lockfile — because
"works on my machine" is not a deploy story.

## What I'd tell someone starting this

* **Build the LP baseline first.** It reframes every downstream claim, and
  if your optimizer can't match it, you want to know in week one.
* **Choose correlations you can cite.** The G&H conversion range, the
  Haverly RVP index, the ICCT hydrotreater loss — each one is a footnote, and
  the footnotes are the credibility.
* **Report the metric that can go badly.** Leave-crude-out is the metric
  with information; random k-fold alone is marketing.
* **Prefer the boring finding stated plainly** (DE = LP; the physics are
  linear) **to an exciting one you can't defend.**

---

*The dashboard lives on Hugging Face Spaces, the full repo — 137 tests,
methodology with per-constant citations, and a provenance table for every
input — is on GitHub. Everything runs on free tiers; everything is MIT.*

**Stack:** Python 3.12, pandas/NumPy, scikit-learn, SciPy (vectorized DE +
linprog), marimo, Plotly, uv, GitHub Actions, Hugging Face Spaces, EIA Open
Data v2.
