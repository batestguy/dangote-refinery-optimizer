# Plan Review & Improvement Spec
## Dangote Refinery Production Planning & Feedstock Optimization — v0.1 Review

**Spec date:** 2026-09-18
**Rev. 2026-09-18 (post-spec review):** App framework switched from Streamlit to **marimo** (all-in: notebooks + app on HF Spaces) after user decision; see §3.7, §4 rows 12/15/19–20, §5 Phase 6, §6.
**Prepared from:** `idea.txt` (master brief v0.1), independent verification of data sources, and a 4-round structured interview (18 answered questions).
**Scope of this document:** A comprehensive critique of the plan + a prioritized improvement roadmap + a risk register + all decisions locked during the interview. **No code has been written.** This spec governs Phase 0.

---

## 1. Executive Summary

The plan is unusually strong for a portfolio project: real mathematical formulation (§3.2 of the brief), a published-methodology backbone (ETR + DE), a disciplined scope guard (4 products, ~5 crudes, single period), and a recruiter-aware CV mapping. It avoids the classic failure modes of "predict house prices" projects.

However, the review found **one structural flaw, three data gaps, and a set of process improvements**. None are fatal, but two of them (the assay→yield bridge and the pricing-data gap) would sink the project's credibility if discovered by a technical interviewer rather than fixed in design.

### Headline findings

| # | Finding | Severity | Section |
|---|---------|----------|---------|
| F1 | **The assay→yield join does not exist.** Crude assays describe feed; unit yields come from process data (FCCU). These datasets share no key. The surrogate as briefed has no training signal for "blend → yields." | 🔴 Critical | §3.1 |
| F2 | **Electric Sheep pricing dataset is ~27 rows / 3.6 kB.** It cannot anchor a 25-year economics layer as the brief implies. | 🔴 Critical | §3.2 |
| F3 | **CrudeOilMix verified real** (1,141,933 simulator-generated blend samples from 9,061 real assays, CC-BY-4.0, parquet, 10M–100M rows category) — but it's a *NeurIPS benchmark* with multimodal structure; treat as dataset, not turnkey solution. | ✅ Resolved risk | §3.1 |
| F4 | **No product quality specs** in the objective as briefed — a refinery planner without octane/sulfur caps looks naive to domain reviewers. | 🟠 Major | §3.3 |
| F5 | **Baseline definition is vague** ("margin improvement over baseline") — the honest baseline is an LP optimum, not a strawman. | 🟠 Major | §3.4 |
| F6 | Random k-fold CV on correlated blend samples inflates R²; a leave-crude-out protocol is needed for an honest generalization claim. | 🟠 Major | §3.5 |
| F7 | "Optimal temperatures/catalyst ratios" with zero real unit data risks invented-precision criticism. Blend + one flagship severity variable was chosen instead. | 🟡 Moderate | §3.6 |
| F8 | Streamlit Cloud 1 GB RAM + deep re-optimization UX (30–60 s runs) is workable but needs engineering discipline (caching, budgeted DE). | 🟡 Moderate | §3.7 |
| F9 | Process gaps: repo visibility, CI depth, tooling, descope order, and phase-2 feedback loop were all undecided in the brief. | 🟡 Moderate | §4 |

---

## 2. What the Plan Gets Right (Keep As-Is)

1. **Problem formulation (brief §3).** Objective function, decision variables, and constraints are correctly structured for a refinery blending problem. Linear blending rules for API gravity and sulfur are the industry-standard approximation — appropriate here.
2. **Scope guard.** 4 products × ~5 crudes × single period is the right size. The brief's own §10.2 "scope creep = highest project risk" is correct and this spec enforces it.
3. **Methodology pairing.** ETR surrogate + SciPy differential evolution is a defensible, published pattern (cf. Umeozor 2026, *Applied ML Models to Oil Refinery Programming*; Mohd Fadzil et al. 2023, *Ind. Eng. Chem. Res.*; Saghir et al. 2024 on surrogate + evolutionary optimization). Replicating-then-extending a published method is exactly the right portfolio move.
4. **Deployment realism.** Streamlit Community Cloud as primary, GitHub Actions for CI, HF Space for portfolio page is the correct free-tier stack in 2026. The brief's own comparison table (§7.1) is accurate.
5. **Transparency stance.** The brief's §10.3 framing ("methodology demo, synthetic data disclosed") is the correct legal and credibility posture and is strengthened in this spec.
6. **Non-goals (brief §1.5).** Correctly excludes real-time trading, proprietary data, and Aspen-class simulation.

---

## 3. Detailed Critique

### 3.1 The structural flaw: no assay→yield bridge (F1)

**The problem, precisely.** The brief's objective is
`max Σ (predicted_yield_i × price_i) − Σ (blend_ratio_j × cost_j)`.
`predicted_yield_i` implies a model `f(crude properties, process conditions) → yields`. But:

- **CrudeOilMix** (verified: HF `anon12-neurips-2026/CrudeOilMix`) contains whole-crude properties, blend composition, TBP curves, and *simulator-generated blend properties* — not unit yields.
- **FCCU dataset** (mlforpse.com) contains unit operating data → yields, but for *specific feeds*, with no linkage to the assay slate.
- Joining them on crude_id is impossible: different feeds, no shared identifiers.

A surrogate trained by naively concatenating these two tables would either (a) fail to learn, or (b) learn spurious correlations that collapse under leave-crude-out validation (F6). **This is the single most important design decision left open by the brief** (interview answer: "You decide in spec").

**Recommended solution: Two-stage "pseudo-refinery" bridge (hybrid of the interviewed options).**

```
Stage 1 — TBP cut-point mass balance (the bridge):
  For each crude in the slate (from real public assays, not CrudeOilMix):
    • TBP curve → cut fractions: naphtha (<180°C), middle distillate
      (180–360°C), VGO (360–540°C), residue (>540°C)
    • Apply standard conversion factors per unit:
        - FCC: VGO → gasoline/LCOalkyl feed, yield correlated with
          API & Conradson carbon (published FCC yield correlations)
        - Hydrotreating/HDS: sulfur pickup on diesel/jet streams
        - Reformer: naphtha → gasoline w/ octane uplift
    • Output: per-crude *theoretical yield vector* y_j (4 products)
      under a reference unit configuration.

Stage 2 — ETR surrogate learns the residual:
  Inputs : blend-weighted crude properties (API, sulfur, TBP PCA components),
           FCC severity variable, crude identity features
  Labels : Stage-1 yield vectors, perturbed/calibrated using FCCU dataset
           statistics (yield-vs-severity behavior) so the model learns
           realistic response surfaces, not just linear interpolation.
  Output : yield_i(x_blend, severity) for the optimizer.

Why this wins:
  • Every number in the pipeline is traceable to a published correlation
    or a real dataset → interviewer-defensible.
  • The FCCU data provides *shape* (yield response to severity); the
    assays provide *level* (what a crude can yield). Both are used honestly.
  • The pseudo-refinery is itself a portfolio artifact ("built a cut-point
    mass-balance model of a refinery") — a differentiator.
```

**Alternatives rejected:** pure FCCU-only training (loses blend variation the DE needs to explore); pure CrudeOilMix (no yield labels — confirmed from its card); first-principles simulation (out of scope per brief §1.5).

**Effort impact:** +1 week (the brief's Phase 2 doubles in importance). The 11-week plan becomes ~12. See §5.

### 3.2 The economics gap: pricing data (F2)

**Verified:** `electricsheepafrica/africa-synth-energy-oilgas-crude-pricing-nigeria` = **27 rows, 3.59 kB CSV**. The brief's "1999–2025 Bonny Light, Forcados" framing materially oversells it. It is useful as a *schema reference and qualitative texture*, not as an economics anchor.

**Decision (interview: Hybrid):**

- **Historical anchor for modeling:** EIA Open Data v2 — US product prices (gasoline, diesel, jet/kero), crack spread proxies, and refinery utilization. Free API key required (register at eia.gov/opendata).
- **Bonny Light / Forcados spot:** pull from public spot series (e.g., NG Weekly Petroleum / NUPRC publications, Platts-substitutes documented in `docs/data_provenance.md`). Where a series cannot be sourced freely, use the EIA Brent−(differential) convention and *document the differential assumption*.
- **Live layer for dashboard:** EIA real-time + `open.er-api.com` FX (as briefed).
- **Electric Sheep data:** retained for Dangote metadata (capacity 650 kbpd, utilization ~0.8) and as qualitative context; clearly labeled synthetic in all outputs.
- **New artifact:** `docs/data_provenance.md` — one table per price/cost input: source URL, license, pull date, transformation. This directly answers the "is this real?" interviewer question.

### 3.3 Quality specs (F4) — decision: **full spec bundle**

Interview answer: full bundle (octane, cetane, sulfur, freeze point, RVP). This is the most ambitious answer available and changes the formulation:

- Adds linear blending index (LBI) constraints for: gasoline RON (≥ 91/95 blend target), diesel sulfur (≤ 50 ppm blend), jet freeze point, diesel cetane index, gasoline RVP.
- Implementation: properties blended via standard industry mixing rules (LBI for octane/cetane/RVP; linear for sulfur; linear-by-weight for freeze point proxy). Each rule cited in `docs/methodology.md`.
- **Risk acknowledged:** this is the largest new modeling surface. Mitigation: specs enter as **constraints** (the optimizer must satisfy them), not as extra surrogate outputs — no new ML burden. Where a crude property is missing from a public assay (common), use the CrudeOilMix `wc_ent` modality or flag-and-impute with documented defaults.

### 3.4 Baseline definition (F5) — decision: **both + random**

The headline claim "X% margin improvement" is now defined as a 3-way comparison, all under the *same* price vector and constraints:

1. **Equal-weight blend** of the 5-crude slate at default severity (the intuitive baseline).
2. **Random search** (10k feasible draws, take the best) — bounds what "search" alone achieves.
3. **LP optimum** on the linearized model (SciPy `linprog` or PuLP) — the honest ceiling for any linear approach; DE only "wins" if nonlinear yield response creates real gains.

Report all three plus DE in one table in the README and dashboard. If DE ≤ LP, *say so and explain why* (the nonlinearity may be small at 5 crudes — that itself is a finding worth publishing; it de-risks the project from failure).

### 3.5 Validation design (F6) — decision: **both, reported side-by-side**

- **Headline metric:** 5-fold random CV R² (competitive, comparable to published numbers).
- **Honesty metric:** GroupKFold leaving entire base crudes out — "the model has never seen this crude." Expected to drop R² substantially; this drop is *reported prominently in the model card*, not hidden. Framing: "R²_random = X, R²_unseen-crude = Y; the gap quantifies interpolation vs. extrapolation risk."
- Never present only the random k-fold number. An interviewer who spots correlated-sample leakage will assume the worst.

### 3.6 Decision-variable scope (F7) — decision: **blend + FCC severity**

- Variables: 5 blend ratios (Σx = 1) + 1 FCC severity proxy (e.g., reactor temperature mapped to conversion via the Stage-1 correlation). Total 5–6 continuous dimensions — small, fast, robust for DE.
- The brief's per-unit temperatures/catalyst ratios are **despecified to future work** with an explicit README note: "unit-level configuration requires plant data this project does not claim to have."
- This directly defuses the "where did these temperatures come from?" question.

### 3.7 Dashboard & runtime (F8) — decision: **deep re-opt on marimo, hosted on HF Spaces** (revised post-spec)

User chose **all-in marimo**: one framework for the narrative notebooks *and* the deployed app. This replaces the earlier Streamlit decision. Rationale: single stack to learn/maintain, reactive cells (no hidden state bugs), .py-native (Git-diffable, importable from `src/`), and a genuinely modern 2026 signal.

- **App = a marimo notebook** (`app/app.py`) importing the same `src/optimization` + `src/models` modules the analysis uses — no logic duplication.
- **Hosting:** Hugging Face Space via the official `marimo-team/marimo-app-template` fork (verified: replace `app.py`, list deps in `requirements.txt`, auto-deploy). Free CPU tier.
- **Deep re-opt UX kept:** full DE run on click (30–60 s) with marimo's `mo.status.spinner()` / progress output; cached model + price tables (`functools.lru_cache` / module-level load).
- **RAM headroom improves:** free HF CPU Spaces (~2 vCPU / 16 GB) far exceed Streamlit Cloud's 1 GB — the model-size guard relaxes, though ETR ≤500 trees / .pkl <50 MB stays as good practice.
- **New trade-off to manage:** HF Spaces sleep after ~48 h inactivity and cold-start in ~30–60 s; marimo is younger than Streamlit (CVE-2026-39987 RCE was patched — pin the fixed release, disable file-upload widgets, no arbitrary `mo.ui` code execution surfaces).
- **De-risk fallback (pre-committed):** all optimization/model logic lives in `src/`, so if marimo deployment proves unstable in Phase 6, porting the app shell to Streamlit is a ≤2-day job with zero model rework.
- Keep the briefed live FX + WTI tickers (cheap, add "live" credibility).

### 3.8 Smaller items from the critique

- **idea.txt is 100% brief and 0% journal** — good. But §9 "Open Questions" should be actively migrated to a "Decided" table as interview decisions are executed; otherwise agents and future-self re-litigate settled questions (brief Appendix E anticipates this).
- **Success criteria (brief §1.4)** should add the honesty metric: "R²_unseen-crude" alongside headline R², so the "impressive" bar isn't gamed by leakage.
- **Add `CHANGELOG.md`** from day 1 (brief §Appendix G already has the shape) — cheap recruiter signal of process maturity.

---

## 4. Decisions Locked in Interview (18 answers)

| # | Question | Decision |
|---|----------|----------|
| 1 | Deliverable of this review | Comprehensive: critique + roadmap + risk register |
| 2 | Current status | Truly pre-code; plan itself is open for revision |
| 3 | Time budget | ~40 hrs/week — 11-week plan roughly right (now ~12 with bridge) |
| 4 | Primary audience | Mixed/general — README must read well for DS/ML, quant, and energy-domain reviewers |
| 5 | Assay→yield bridge | Agent to analyze options in spec → **two-stage pseudo-refinery bridge** (§3.1) |
| 6 | CrudeOilMix scale | **Minimal first:** Nigerian subset + small global slate; scale only if R² disappoints |
| 7 | Pricing anchor | **Hybrid:** EIA historical for modeling + live EIA/FX in dashboard; Electric Sheep demoted to context |
| 8 | Baseline | **Equal-weight + random search + LP optimum** (3-way table) |
| 9 | Decision variables | **Blend ratios + FCC severity** (unit-level tuning despecified) |
| 10 | CV strategy | **Report both** random 5-fold and leave-crude-out |
| 11 | Tooling | **uv** + pyproject.toml (2026 signal) |
| 12 | Code layout | **Hybrid:** src/ from day 1 + polished narrative notebook per phase importing from src/ — *(rev: notebooks are **marimo** .py files, not Jupyter)* |
| 13 | Descope order | Scenario analysis cut first |
| 14 | Quality specs | **Full bundle** (RON, sulfur, cetane, freeze point, RVP) as constraints |
| 15 | App behavior | **Deep re-opt** (30–60 s) with progress UX |
| 16 | CI depth | **pytest + ruff** |
| 17 | Repo visibility | **Public day 1**, README states WIP |
| 18 | Scenario fallback | **3-scenario mini** (bull/base/bear deterministic re-optimization) replaces 10k-iteration Monte Carlo if behind |
| 19 | *(rev) App framework* | **marimo** replaces Streamlit — app is a marimo notebook on HF Spaces; Streamlit demoted to documented fallback |
| 20 | *(rev) Notebooks* | **marimo** replaces Jupyter for all narrative/analysis notebooks (reactive, Git-diffable, .py) |

---

## 5. Revised Roadmap (12 weeks @ ~40 h/wk)

Deltas vs. brief §6 are marked. Order reflects new dependencies (bridge before features; quality specs enter with constraints, not ML).

| Phase | Weeks | Content (changes in **bold**) |
|-------|-------|-------------------------------|
| 0. Framing & scaffold | 1 | Problem statement doc; **uv + pyproject**; repo **public**; CI (**pytest+ruff**); `.env.example` (EIA key); README with WIP + transparency statement; **`docs/data_provenance.md`** |
| 1. Data acquisition | 2–3 | EIA historical pulls; **public assay scraping/parsing (ExxonMobil, TotalEnergies, Equinor, NUPRC)**; Electric Sheep metadata only; **FCCU dataset**; **defer full CrudeOilMix download** (pull only needed columns/strata — minimal-first decision) |
| 2. **Bridge** (was: EDA/features) | 4–5 | **Stage-1 pseudo-refinery: TBP cut-points + published FCC/HDS/reformer correlations → per-crude yield vectors;** calibrate shape vs. FCCU data; EDA (marimo notebooks); TBP PCA; blend-weighted features; **quality-spec blend indices** |
| 3. Surrogate model | 6–7 | ETR primary; **dual CV protocol (random + leave-crude-out)**; SHAP; model card with **both** R² numbers; comparisons XGB/LGBM as budget allows |
| 4. Optimization | 8 | DE (blend + severity, 5–6 vars); **LP/random/equal-weight 3-way baseline table**; sensitivity (100 seeds); convergence plots |
| 5. Scenario analysis | 9 | Monte Carlo 10k as briefed, **with the 3-scenario mini as the pre-agreed descope fallback** |
| 6. Dashboard & deploy | 10 | **marimo app on HF Spaces** (template fork); deep re-opt UX (30–60 s, spinner/progress, cached artifacts); **pin patched marimo release**; live FX/WTI; HF Static Space portfolio page links to app |
| 7. Documentation & packaging | 11 | Blog post, executive summary, video, interview talking points; **CHANGELOG maintained since week 1** |
| Buffer | 12 | Absorbs the bridge overrun; may roll Phase 5 scope forward |

**Critical path:** Phase 2 (bridge) → Phase 3 (surrogate) → Phase 4 (optimization). Everything else can slip a week without moving the ship date.

**First two weeks of concrete actions (Phase 0):**
1. `uv init`, pyproject with pinned deps, src layout (`src/{data,features,models,optimization,viz}`), pytest + ruff wired, GH Actions on push.
2. Register EIA API key; store in `.env` (gitignored); `.env.example` committed.
3. `docs/problem_statement.md`: the §3.2 formulation amended with (a) severity variable, (b) quality-spec constraint block, (c) the 3-way baseline definition.
4. `docs/data_provenance.md` skeleton with one verified row per source (CrudeOilMix card, EIA series IDs, assay URLs).
5. README: one-paragraph pitch, transparency statement, "WIP" banner, roadmap table mirroring §5 above.

---

## 6. Risk Register (updated)

| Risk | P | I | Mitigation (delta from brief §10 in bold) |
|------|---|---|-------------------------------------------|
| Assay→yield bridge yields implausible yield vectors | M | H | Use published correlations only; sanity-band check against public refinery yield ranges (e.g., a light sweet crude cannot yield 60% gasoline without conversion); FCCU calibration; **kill-switch: if Stage 1 fails validation, fall back to blend-only linear model + LP and reframe project as "optimization-first"** |
| Leave-crude-out R² drops far below headline | H | M | **Expected by design**; report the gap as a finding; frame "model interpolates within crude families, extrapolation flagged" |
| Quality-spec constraints make LP infeasible for some slates | M | M | Add soft-constraint mode (penalty tuning) as debug tool; slate selection in Phase 1 includes ≥2 light sweet crudes to keep feasibility easy |
| CrudeOilMix full download too heavy locally | M | L | Minimal-first (locked): column selection + stratified sample only |
| EIA series gaps or API changes | L | M | Cache raw pulls to parquet in `data/raw/`; provenance doc records pull dates; manual fallback CSV documented |
| DE margin gain ≤ LP baseline | M | M | Pre-committed framing: report honestly; the LP comparison is itself the rigor signal; explore nonlinear-only gains (severity interaction) before claiming |
| HF Spaces sleep (48 h) + 30–60 s cold start on recruiter visit | M | M | Pre-computed fallback result renders instantly on load; README shows expected latency; link from GitHub README so a sleeping Space is not the first impression |
| marimo maturity (young framework; CVE-2026-39987 precedent) | L | M | Pin patched release; no file-upload or code-execution widgets in public app; **pre-committed Streamlit fallback** (≤2-day port since all logic lives in src/) |
| Scope creep (brief's own #1 risk) | H | H | Locked decision table (§4) is the contract; changes require updating this spec, not ad-hoc brief edits |
| Synthetic-data credibility | M | H | Provenance doc + dashboard "About" modal stating exactly which layers are synthetic vs. real |
| Time overrun | M | M | 12-week plan with buffer; descope order locked (scenario first, per interview) |

---

## 7. Explicit Non-Goals (unchanged from brief, restated as contract)

- No proprietary/NDA Dangote data; no claims about Dangote's actual operations.
- No real-time trading/procurement system.
- No Aspen-class rigorous simulation; published correlations only.
- No unit-level "optimal temperatures" presented as findings (despecified per §3.6).
- No authentication on the app; no paid-tier services.

---

## 8. Open Items (for future spec revisions)

1. Exact slate of 5 crudes (candidates: Bonny Light, Forcados, Qua Iboe + 2 global grades, e.g., Arab Light, Urals) — final choice in Phase 1 after assay availability check.
2. Specific FCC yield correlation set to implement (candidates: Maple & Leitzell style API correlations, or rule tables from public refining textbooks) — decide in Phase 2 kickoff.
3. Whether the dashboard includes the LP baseline as a toggle ("show me the linear ceiling") — cheap and impressive; default yes.
4. Blog platform (brief leans Medium + personal site) — decide Phase 7.
5. marimo release pin: verify CVE-2026-39987 fixed version at Phase 6 kickoff and record it in `pyproject.toml`.
6. Whether the HF Space uses the free CPU basic (16 GB) or upgrades — revisit only if DE runs exceed the 30–60 s budget.

---

*This spec supersedes the open questions in idea.txt §9 for the items listed in §4. `knowledge.md` remains the orientation file for agents; this document governs Phase 0 planning.*
