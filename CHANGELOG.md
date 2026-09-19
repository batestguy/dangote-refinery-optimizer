# Changelog

All notable changes to this project. Format based on Keep a Changelog.

## [Unreleased]

### Added
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
