# Changelog

All notable changes to this project. Format based on Keep a Changelog.

## [Unreleased]

### Added
- **In-browser interactive dashboard live on GitHub Pages**
  (https://batestguy.github.io/dangote-refinery-optimizer/): the full marimo
  app exported via `html-wasm` — Python runs in the visitor's browser
  (Pyodide), no server, no sleep, no PRO tier. A startup step installs the
  `dangote_opt` wheel and copies the bundled `public/` data into the
  browser filesystem; failed package downloads are retried, and a reload
  notice is shown if they still fail. Phone layout pass: section 03 stacks,
  hero titles stay visible, the tornado is interactive, the fan chart
  scrolls horizontally, and Run shows a spinner. The first visit can take
  up to ~5 minutes: the README says so, and `scripts/patch_wasm_index.py`
  (run after export) puts a notice with an elapsed-time counter on marimo's
  loading screen, because the in-app callout only appears near the end of
  the wait. Verified with Playwright on desktop and Pixel 7 emulation.

### Added
- **HF Static portfolio Space live**
  ([JBZABC/dangote-optimizer-portfolio](https://huggingface.co/spaces/JBZABC/dangote-optimizer-portfolio)):
  headline-results table, methodology credibility section, links to the repo.
  ⚠️ The interactive Docker Space is blocked on HF's free tier (Docker Spaces
  now require PRO) — the portfolio links the repo's marimo app instead;
  `deploy/hf-push-runbook.md` + `scripts/build_space_root.py` stay ready for
  a PRO upgrade.

### Changed
- **Dashboard retheme: light corporate identity in the Dangote brand palette**
  (`app/app.py`). Direction from the project owner: the dashboard targets
  Dangote, so it wears the logo's colors — navy indigo `#171D64` ("Lucky
  Point", Pantone 2756C) + flare red `#F0513A` ("Flare", Pantone 7625C),
  cited to schemecolor.com's Dangote Cement palette and "The Dangote Color
  Strategy" (LinkedIn). Paper-white canvas (`#f7f8fc`), navy hero panel with
  the red arc re-created as a 6px top rule over the Lekki photo gradient,
  navy/red KPI accents, white-backed matplotlib fan/tornado plates now blend
  seamlessly (the old dark-theme mismatch resolves itself). Plotly template
  renamed `console` → `dangote` (light grid, ink-toned labels); pills,
  callouts, tables, stepper and links re-derivated. Palette-only by choice:
  no actual logo asset (trademark; the repo is an unaffiliated methodology
  demo). Verified: marimo check clean, 137 tests, ruff, headless export both
  model paths (pkl + pkl-hidden Space condition), browser screenshot probes
  (hero band ≈ #171D64, body #f7f8fc), console clean.
- **Risk figures rebranded + tornado overlap fix** (`scripts/run_scenarios.py`,
  regenerated PNGs): the margin fan and tornado charts now use the brand
  palette (navy bars/quantile bands, red/ink accents, muted axes) instead of
  matplotlib defaults, and the tornado's value labels no longer collide with
  the axis or bars — labels sit inside wide bars (white on navy/red split at
  the base margin: red = worse than base, navy = better) and outside only for
  narrow bars, with explicit xlim headroom. Regeneration is deterministic:
  `scenarios_phase5.json` re-verified byte-identical on every metric (same
  seed), only `generated_utc` moved.
- **Section 03 procedures photo strip** (`app/app.py`): three credited photos
  of actual petrochemical work at the Lekki site — FrankvEck's Commons series
  "Dangote-petro-chemical-procedures" (files 2/7/11, three distinct shoots,
  CC BY-SA 4.0, Commons-API-verified) — downscaled (~131 KB total) and
  base64-embedded like the hero, so the cold-start/no-external-requests
  guarantee holds; responsive 3→1-column strip with inline credits;
  `CREDITS.md` + provenance row 3b updated; Space assembly ships them.
- **Hero photo refreshed** (`app/app.py`): the previous hero (GodwinPaya,
  shot May 2018 — construction era) was the oldest freely licensed image in
  the set; replaced with the newest freely licensed plant imagery on Commons
  (FrankvEck series file 8, shot 2022-06-24), center-cropped to the hero
  frame (248 KB, base64-embedded) with a dated credit chip on the hero
  panel. Commons holds nothing freely licensed newer than June 2022 — the
  refresh path is documented in provenance row 3b.
- **Strip re-curated for human scale**: a scan of the entire Commons Dangote
  category (skin-tone signature + description metadata) found exactly one
  freely licensed photo with people — the delivery of the 3,000-ton RFCC
  regenerator, where workers beside the vessel give the scale. The strip now
  leads with **Aliko Dangote on site at Lekki** (Oct 2022, CC BY-SA 4.0,
  categorized in Commons' "Aliko Dangote" + "Dangote Refinery" categories —
  the only freely licensed on-site photo of him at the plant), followed by
  the regenerator delivery and the preheating train; captions/credits state
  exactly what each photo documents.
- **Section 03 lead photo → the crude tanker**: the main image is now
  "Vessel at Dangote refinery site, Lagos" (GodwinPaya, CC BY-SA 4.0) with a
  caption tying it to the optimization story — the crude the optimizer buys
  arrives as one of these cargoes — while keeping the cited FCC-severity
  fact; the retired CDU close-up is documented in CREDITS.md.

### Added
- **Real refinery imagery, credited** (dashboard): two CC BY-SA 4.0 photos of
  the actual Dangote Refinery at Lekki from Wikimedia Commons — site hero
  (GodwinPaya) embedded as a base64 data URI behind the hero panel's graphite
  gradient (356 KB, zero cold-start requests) and the crude distillation unit
  (FrankvEck) anchoring section 03 beside a decision-summary card tying the
  severity variable to the real CDU. Inline credit links, `CREDITS.md`
  sidecar, provenance row 3b; Space assembly ships the assets. License
  metadata via the Commons API (never hand-build upload.wikimedia URLs).
- **HF Space assembly + verification pipeline** (`scripts/build_space_root.py`,
  `deploy/hf-push-runbook.md`): assembles `deploy/space_root/` (gitignored
  build artifact) — the exact tree to push — with deploy-safety assertions:
  no `.env`, no `*.pkl`, derived-artifact completeness, marimo CVE floor,
  and a pin-vs-lock drift guard; generates the Space `README.md` (Docker
  frontmatter). The tree passed a **Space simulation** — headless app export
  inside `deploy/space_root/` with the local package uninstalled, i.e. the
  exact image condition — which caught a real deploy blocker: the template
  Dockerfile never installs the app's own package, fixed with one documented
  line (`ENV PYTHONPATH=/app/src`; HF marimo docs sanction Dockerfile
  modification). The drift guard also caught `deploy/requirements.txt` having
  been derived from `uv pip list` (drifted venv: numpy 2.5.3/scipy 1.18.1)
  instead of `uv.lock` (2.4.6/1.17.1) — regenerated lock-true.
- **HF Static portfolio page content** (`deploy/portfolio/README.md`):
  headline-results table, links to the app Space and repo, credibility
  framing — `YOUR_HF_USERNAME` placeholder to fill at push.
- **Phase 7 drafts** (`docs/executive-summary.md`, `docs/blog-post.md`):
  answer-first exec brief with the headline-numbers table and planner risk
  framing; publication-ready blog post ("The honest optimizer") built on the
  DE = LP structural finding. Talking points + video remain.
- **Phase 6 live market ticker** (`data/ticker.py`, `scripts/refresh_ticker_snapshot.py`,
  app cell): NGN/USD FX from open.er-api.com (provenance row 8, keyless, 1 h
  disk cache) + WTI spot via a new `wti_spot_daily` EIA catalog entry
  (`petroleum/pri/spt`, product `EPCWTI`, process `PF4`, duoarea **`YCUOK`**
  — probed live 2026-09-23, the only area the product carries on this route;
  same pattern as Brent's `ZEU`). Both feeds verified live (FX 1,328.371
  NGN/USD; WTI $107.02 daily 2026-09-15); every failure mode degrades to a
  timestamped stale/snapshot value — committed
  `data/derived/ticker_latest.json` is the cold-start-safe fallback the app
  renders on HF Spaces (refresh before each deploy). Display-only: neither
  feed enters the optimization (USD price-taker, spec §7). 10 new offline
  tests via injectable transports (137 total).
- **HF Space deploy kit** (`deploy/`): Space `requirements.txt` pinned to the
  exact `uv.lock` versions (marimo 0.24.2 — CVE-2026-39987 floor satisfied),
  verbatim mirror of the official marimo template Dockerfile (Docker SDK,
  port 7860, non-root user), and a deploy checklist with the cold-start
  acceptance gate (precomputed content < 2 s) and a no-secrets-in-tree
  verification step. Committing `data/derived/` artifacts is what makes the
  Space render instantly on cold start — no pkl, no raw caches, no `.env`.
- **Phase 5 scenario analysis** (`optimization/scenarios.py`,
  `scripts/run_scenarios.py`): 10,000-draw Monte Carlo over correlated price
  scenarios — historical block bootstrap (12-month blocks of EIA Δlog prices,
  Brent + USGC products 2015–2025) answers the brief's open questions
  empirically (distribution = bootstrap; correlated shocks = inherited from
  real co-moves; FX/demand = documented out-of-scope, USD price-taker). Every
  draw re-optimizes via the exact LP (Phase 4 skeleton re-solve, ~8.5 ms/draw).
  Headline: mean $17.68 ± 8.29, **VaR(5%) $6.25 / CVaR(5%) $1.42 / P(loss)
  0.8%**; fixed-blend comparison shows **re-optimization is worth +$2.56/bbl
  and flips the tail from −$3.50 to +$1.42 CVaR** — a risk lever, not just
  profit. Two-regime diet (ANS 50.5% / Forcados 47.9% of draws). Artifacts:
  `data/derived/scenarios_phase5.json` + fan/tornado figures in `docs/assets/`;
  app renders the precomputed summary (HF cold-start-safe). Tests pin the
  math: zero-draws ≡ base LP, Brent-shift argmax invariance, VaR/CVaR
  relations, tornado monotonicity (127 tests).
- **Phase 4 optimization driver + baseline contract** (`optimization/de_driver.py`,
  `optimization/baselines.py`, `viz/convergence.py`, `scripts/sensitivity_study.py`):
  vectorized DE (scipy `vectorized=True` over exact batch paths) with
  convergence capture, Sobol init, runtime/budget flag; the mandatory 3-way
  baseline table — equal-weight, random search (10k feasible draws, batched),
  and an **exact LP** over the bridge's affine-in-severity physics (substitution
  `u_j = s·x_j`; quality specs as hard linear constraints from the same
  `BatchQualityModel` coefficients as the DE penalty). Key structural finding:
  **DE matches the exact LP to <0.5¢/bbl** — the bridge physics are linear in
  the decision variables, so the honest bar (problem statement §4) is met
  exactly, mechanism explained in methodology §6a. **Performance: DE run
  0.85 s on the bridge / ~3.4 s through the ETR (was ~127 s scalar)** —
  ~20× headroom inside the 30–60 s app budget (spec §3.7). 100-seed
  sensitivity sweep committed (`data/derived/sensitivity_phase4.json`, mean
  $15.84 ± 0.00, uplift vs equal-weight +11.3%) with figures in `docs/assets/`.
  Batch-path exactness (bridge, quality mirror, objective) pinned to machine
  precision in `tests/test_phase4.py`; 121 tests.
- **Phase 3 ETR surrogate** (`models/dataset.py`, `models/train_surrogate.py`,
  `scripts/train_surrogate.py`): Extremely Randomized Trees trained on
  bridge-generated labels (4,000 Dirichlet-sampled blends × severity, seed
  20260919) behind the existing `YieldModel`/`quality_model` hooks — one
  mass balance, two engines. Dual-CV protocol per spec §3.5: random 5-fold
  (headline) min R² = 0.982 (impressive gate >0.90 passed) + leave-crude-out
  GroupKFold (honesty) — the jet LCO collapse (R² ≈ 0.11) is quantified and
  explained in the committed `models/model_card.md` (tree ensembles cannot
  extrapolate below the held-out crude's range). Surrogate fidelity inside the
  envelope: max |Δyield| ≈ 0.0007 vs bridge; DE optimum unchanged. Model size
  capped at 21.3 MB (150×14×4 sweep; 300 trees = 96.5 MB violated the 50 MB
  hosting guard). pkl is gitignored and regenerates deterministically in ~5 s;
  app loads it with bridge fallback, permutation importance in the card.
- FCCU calibration finding (provenance row 7): the planned yield-vs-severity
  calibration against the MIT ML-PSE FCCU dataset was probed and **dropped** —
  it is fault-detection data (NOC envelope + equipment faults, no severity
  sweep), so the surrogate inherits the bridge's cited G&H severity shape.
- Quality-spec constraint bundle (spec §4 decision 14 — Phase 2 deliverable):
  `features/quality.py` computes gasoline RON (linear), RVP (psi^1.25 index,
  Haverly), jet freeze point, and diesel cetane (linear) from the bridge's
  component streams; enforced via `RefineryObjective.quality_model` (injectable,
  same pattern as the Phase 3 ETR hook) with the linear+quadratic penalty.
- Bridge octane units (methodology §3b): isomerization (light naphtha),
  reforming (85% reformate, G&H ch. 9), alkylation (50% of FCC gas+coke), and
  butane pull-off (25% of light naphtha → LPG for RVP control); `component_volumes()`
  exposes the pre-pooling streams — one mass balance behind yields and quality
  (mass-balance equivalence pinned in tests). Without these units no realistic
  blend meets RON 91 (SR naphtha blends at RON ≈ 58).
- Product-price anchor: `data/prices.py` wires the verified EIA USGC spot
  series (gasoline EPMRU / ULSD EPD2DXL0 / jet EPJK, $/gal × 42 → $/bbl,
  12-mo averages: $84.77 / $93.49 / $88.94) into the objective; petrochem pool
  stays on a disclosed PLACEHOLDER (no citable EIA spot exists for the
  LPG/propylene/residue basket — probed; refresh path documented).
  Committed artifact `data/derived/prices_phase2.parquet` + sidecar
  (`scripts/build_prices.py`). 20 new tests (102 total).
- Cost anchor (provenance row 9 complete): `brent_spot` series live-verified
  and added to the EIA catalog (duoarea `ZEU` — Brent's only area on the spot
  route); `data/costs.py` models delivered cost = trailing-12m EIA Brent
  ($69.10/bbl as of 2026-09-19) + per-grade differential. Every differential is
  **ASSUMED** with a documented quality rationale (refresh path: OPEC MOMR
  actuals); assumption direction sanity-tested (premium scales with API within
  a sulfur class; sour grades discount; table covers the exact slate, strict
  KeyError on unknown grades). Committed artifact
  `data/derived/costs_phase2.parquet` + sidecar (`scripts/build_costs.py`);
  app wired to real costs with fallback to the committed artifact's Brent
  reference when no key/cache is present. 9 new tests (82 total).
- Phase 2 Stage-1 bridge (`features/bridge.py`): TBP cut-point integration
  (interpolated, basis-uniform vol% curves) + severity-dependent FCC
  conversion (40→80% of VGO, cited Gary & Handwerk ranges) with documented
  product splits; hydrotreater ≈1% yield loss (ICCT exhibit 17); 4-product
  pooling. Ground-truthed: parsed-curve cuts reproduce published Bonny Light
  cut yields to ±0.2 vol%; gas-in-curve simplification quantified (≈2 vol%).
- `docs/methodology.md` — every bridge constant cited (spec §5 Phase 2
  deliverable); Maples correlations reviewed and rejected for
  traceability (documented in §6.1).
- TE assay parser upgraded: curves now stored on the vol% column (uniform
  basis across the slate) — artifact rebuilt.
- `RefineryObjective` accepts an injectable `yield_model` (the exact signature
  the Phase 3 ETR will use); app upgraded from mock slate to the real
  published assays with bridge yields (costs still placeholder until row 9).
- 11 new tests (73 total).

### Changed
- **Dashboard rebuilt as a proper project front page** (`app/app.py`):
  cold-start-first cell order — header → precomputed headline KPI strip
  (margin, uplift, re-opt value, VaR/CVaR/P(loss), surrogate R² straight from
  the committed Phase 4/5 JSONs, zero model load or network) → live market
  ticker → optimal-diet and regime-switch bar charts (plotly, from
  `scenarios_phase5.json` `base_blend`/`switch_share` — the fan/tornado
  figures previously never rendered by the app now appear in the risk
  section) → deep re-opt interaction → collapsed assumptions/methodology/
  reproduce accordions → footer. Assumptions text is built from live objects
  (model-card leave-crude-out keys are `yield_*`-prefixed — verified, not
  indexed from memory). Both model paths verified by headless export: pkl
  present (surrogate KPI + honesty note) and pkl absent (the HF Space
  condition — bridge KPI footnote, bridge-path DE). marimo check back to the
  single pre-existing cosmetic warning; the markdown-indentation warning
  pattern is documented (plain triple-quoted `mo.md` strings get flagged;
  f-strings with real placeholders are exempt).
- **marimo floor pinned at 0.23.0** (Phase 6 kickoff, spec open item 5):
  CVE-2026-39987 — pre-auth RCE via marimo's terminal WebSocket endpoint — is
  fixed in 0.23.0, and the old `>=0.12` floor would resolve a vulnerable
  release on a fresh clone or the HF Space build. `uv.lock` carries 0.24.2,
  already above the new floor, so no lock churn and no behavioral change;
  127 tests, ruff, and `marimo check` all green after the pin (the 1 cosmetic
  check warning is pre-existing).

### Fixed
- Phase 1 data layer: EIA Open Data v2 client (`data/acquire.py`) with
  cache-first parquet + provenance sidecars (key never persisted), page
  pagination with a hard stop, injectable transport for offline tests, and a
  candidate series catalog (`psump`, `tusandm`, `impcus` — verify live once the
  key lands, via `scripts/eia_smoke.py`).
- Assay record schema (`data/assays.py`): provenance-required records enforcing
  the data-provenance quality rules (API 10–50, sulfur 0–5 wt-%, TBP strictly
  increasing 0–100 %) at construction; slate validation (unique ids, exactly 5).
- CrudeOilMix `mix_json` mapper (`data/crudeoilmix.py`): tolerant word-segment
  key matching, explicit unmapped-key surfacing, reject tracking, whole-crude
  streaming filter (no bulk download).
- 35 new offline tests (57 total).
- Five-crude slate finalized from published assays (provenance row 3, spec §8
  item 1): Bonny Light, Forcados (TotalEnergies sheets), Qua Iboe, Alaska North
  Slope, Thunder Horse (ExxonMobil reports). Arab Light/Urals substituted — no
  open TBP assays published. Parsers (`data/assay_parsers.py`) extract
  whole-crude properties + TBP curves with per-crude yield-basis labels;
  cumulative-yield monotonicity added to assay validation. Committed artifact:
  `data/derived/slate_phase1.parquet` + provenance sidecar
  (`scripts/build_slate.py`); PDFs stay in gitignored `data/raw/assays/`.
- EIA catalog live-verified (2026-09-19, key registered): USGC product spot
  prices (gasoline/ULSD/jet, $/gal), US refinery net crude input (area `NUS` —
  `NUS-Z00` has no `YIR` rows), and Nigerian crude imports (`NUS-NNI`); first
  cached parquet + provenance sidecars under `data/raw/eia/`.
- SECURITY: user initially pasted the real EIA key into the committed
  `.env.example`; moved to gitignored `.env`, template restored before staging —
  the key was never committed or pushed.

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
  knowledge.md handover refreshed (2026-09-19 session).

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
