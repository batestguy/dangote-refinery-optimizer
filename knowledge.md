# Project Knowledge

## ★ HANDOFF (2026-09-23, evening) — READ THIS FIRST

**State: Phases 0–5 complete · Phase 6 code-complete (dashboard redesigned,
ticker live, deploy kit verified) · Phase 7 opened (exec summary + blog
drafted) · 137 tests, CI green, all pushed. Remaining: user-side HF Space
push + Phase 7 talking points/video + UI polish (open to suggestions).**

**What the dashboard IS now (2026-09-23, evening):** a dark "refinery control
room" console — graphite `#0f0d0b` + amber crude accents, Barlow Condensed /
IBM Plex Mono, KPI tiles, numbered sections 01–06 with "what you're looking
at" captions, START-here stepper, real CC-licensed photos of the Lekki site
(hero backdrop, base64-embedded) + the CDU unit (section 03), live NGN/USD +
WTI ticker with LIVE/STALE/SNAP badges, deep re-opt with the LP honest bar
wired in ($15.67 vs DE $15.84 through the surrogate), "how to read" callouts.
Local preview: `PYTHONUTF8=1 uv run marimo run app/app.py` (a dev server was
still running on port 2718 at handoff — kill via
`netstat -ano | grep :2718` then `taskkill //PID <pid> //F`).

**⚠️ Run-button "Failed to update value" — ROOT CAUSE KNOWN, not a code bug:**
marimo's **skew protection** rejects clicks from browser tabs holding a stale
server token (exact log line in `/tmp/marimo.log`: `Received request with
invalid server token (skew protection token)… Expected: …, got: …`). Cause:
the server was restarted repeatedly during the redesign while the user's tab
stayed open. **Fix for the user: hard-refresh the tab (Ctrl+F5) or reopen the
URL.** Verified working 3× in fresh automated sessions (result card renders:
DE $15.84 / LP $15.67 / feasible). If it EVER fails after a hard refresh,
check the server log for the token line before touching code.

**Next-session queue (in order):**
1. **UI polish — OPEN TO SUGGESTIONS (user asked to keep this open).** Ideas
   backlog: restyle matplotlib fan/tornado PNGs to dark (they render as white
   plates against the console — biggest visual mismatch left); Run-button
   loading UX (`mo.status.spinner()` around the DE — currently silent for
   ~8–15 s); responsive/mobile pass; contrast/accessibility audit
   (ui-geometry-audit + web-design-guidelines skills exist); possible
   count-up animations, per-product margin waterfall, hover drill-downs.
2. **User-side HF push** — `deploy/hf-push-runbook.md` has exact commands
   (`scripts/build_space_root.py` assembles + asserts; simulation-verified).
   Then fill `YOUR_HF_USERNAME` in `deploy/portfolio/README.md` + add the
   Space badge to README.
3. **Phase 7 remainder:** interview talking points, video, blog platform
   choice (spec §8). `docs/executive-summary.md` + `docs/blog-post.md` are
   publication-ready drafts.
4. Optional/deferred: OPEC MOMR differential refresh, Colab verify, marimo
   narrative notebooks (spec decision 12).

**Quick index of what's where (new this cycle):** design system = first cell
of `app/app.py` (one `<style>`, plain string — CSS braces break f-strings);
Space kit = `deploy/` (Dockerfile with the documented `PYTHONPATH=/app/src`
line, lock-true `requirements.txt`, runbook, portfolio, `space_readme.md`);
assembly = `scripts/build_space_root.py` (hard-fail assertions incl. pin-vs-
lock drift); imagery = `docs/assets/credited/` + `CREDITS.md` (provenance row
3b); ticker = `src/dangote_opt/data/ticker.py` + `tests/test_ticker.py`;
Phase 7 drafts = `docs/executive-summary.md`, `docs/blog-post.md`.
Screenshots live in untracked `output/playwright/`.

Session-by-session detail below; execution log = `docs/setup-steps.md`
(Steps 0–19); architecture/conventions = `AGENTS.md`; number provenance =
`docs/methodology.md` + `docs/data_provenance.md`.

**Headline numbers (for the write-ups / interviews):**

| Result | Value | Where |
|---|---|---|
| Optimal diet (base) | ~100% ANS @ max severity, $15.67/bbl | DE = LP, app |
| Uplift vs equal-weight | +10.0% (impressive gate >10% met) | `sensitivity_phase4.json` |
| DE vs exact LP | ≡ within $0.005 — physics are linear | methodology §6a |
| Surrogate 5-fold R² (min) | 0.982 (gate >0.90 passed); jet LCO 0.11 = honesty finding | `models/model_card.md` |
| Bridge ground truth | ±0.2 vol% vs published cut tables | methodology §5 |
| Re-optimization value | +$2.56/bbl mean; tail CVaR −$3.50 → +$1.42 | `scenarios_phase5.json` |
| Downside risk | VaR(5%) $6.25 · CVaR(5%) $1.42 · P(loss) 0.8% | `scenarios_phase5.json` |
| DE runtime | 0.85 s bridge / 3.4 s surrogate (was 127 s) | 30–60 s budget, 20× headroom |

**Next: Phase 6 (dashboard & deploy)** — in order:
1. ✅ **DONE 2026-09-23:** marimo floor pinned `>=0.23.0` (CVE-2026-39987 =
   pre-auth RCE via terminal WebSocket, fixed in 0.23.0; NVD confirms) —
   `uv.lock` already carried 0.24.2, so no lock churn; tests/ruff/marimo-check
   green. Was `marimo>=0.12`.
2. HF Space deploy — **needs the user's HF account** (create Docker Space →
   push assembled root per `deploy/README.md` → verify cold start renders
   precomputed content <2 s). **Prep done 2026-09-23:** `deploy/` kit ships
   the Space `requirements.txt` (exact uv.lock versions, marimo 0.24.2),
   verbatim template Dockerfile, and the user checklist. Deep re-opt is ~3 s,
   inside budget.
3. ✅ **DONE 2026-09-23:** Live ticker shipped — `data/ticker.py`: NGN/USD FX
   (open.er-api.com, keyless, 1 h disk cache `data/raw/fx/`) + WTI spot via
   new catalog entry `wti_spot_daily` (EIA `pri/spt` DAILY, product `EPCWTI`,
   duoarea **`YCUOK`** — probed live, only area on route, like Brent's `ZEU`).
   Both live-verified (FX 1,328.371; WTI $107.02 @ 2026-09-15). App cell
   renders live→stale→snapshot with as-of dates; committed snapshot
   `data/derived/ticker_latest.json` (`scripts/refresh_ticker_snapshot.py`)
   = the cold-start fallback; display-only (never enters optimization).
   10 new offline tests → **137 tests**. ⚠️ Gotchas: the box's network flaked
   mid-smoke (FX ReadTimeout after curl succeeded seconds earlier — retry
   before diagnosing); catalog lock test (`test_acquire.py`) must be extended
   when adding any CATALOG series.
4. HF Static Space portfolio page linking the app.

**After Phase 6:** Phase 7 (blog post, exec summary, video, talking points) and
the optional marimo narrative notebooks (spec decision 12); OPEC MOMR
differential refresh remains a documented Phase 2+ refresh path.

**Do not re-litigate (settled):** see `AGENTS.md` §"Things to avoid" — marimo,
Maples rejection, FCCU-dataset supersession, slate substitution, ETR size,
scipy vectorized-DE conventions, Brent-shift math, sidecar-based cache reads.

---

## Session Handover (2026-09-23) — Phase 6 kickoff
- **marimo CVE pin DONE:** `pyproject.toml` floor raised `>=0.12` → `>=0.23.0`
  (CVE-2026-39987 pre-auth RCE, fixed 0.23.0; installed 0.24.2 satisfies —
  `uv.lock` untouched, verified with `uv lock --check`). Rationale recorded:
  the old floor would resolve a *vulnerable* release on a fresh clone or the
  HF Space build even though the dev env was patched. Docs updated same commit
  (CHANGELOG `Changed`, setup-steps Step 18 item 1 ✅). 127 tests green.
- **Next up: Step 18 item 2** — HF Space deploy (user must fork
  `marimo-team/marimo-app-template` / create the Space; then `app.py` + pinned
  `requirements.txt` from `uv.lock`; cold-start test <2 s on precomputed cells).
- Then: live FX/WTI ticker (Step 18 item 3), HF Static portfolio page (item 4).

## Session Handover (2026-09-23c) — Phase 6: dashboard rebuild
- **Dashboard rebuilt cold-start-first** (`app/app.py`): header → precomputed
  KPI strip (Phase 4/5 JSONs — no model load, no network) → ticker → diet/
  regime-switch plotly bars (`base_blend`/`switch_share`) → risk table + the
  previously-unrendered fan/tornado PNGs (`mo.image`) → deep re-opt →
  assumptions accordions → footer. ⚠️ Gotchas learned: (1) model-card LCO keys
  are `yield_jet`-prefixed, not `jet` — don't index from memory (KeyError'd a
  cell; headless export caught it); (2) plain triple-quoted `mo.md` strings
  trigger marimo's markdown-indentation warning — make headings data-driven
  f-strings instead; (3) marimo format subcommand doesn't exist in 0.24.x.
  Verified BOTH model paths via `marimo export html` (pkl present + pkl
  hidden = the Space condition: bridge footnote KPI, bridge-path DE, fallback
  model note). `deploy/requirements.txt` now carries `requests` (ticker
  imports it directly) + `plotly` (dashboard charts) explicitly.
- **Next up: unchanged** — Step 18 item 2 user-side HF Space execution.

## Session Handover (2026-09-23f) — imagery + Run-button root cause
- **Photos wired (commit 283675f):** hero backdrop = Lekki site shot
  (GodwinPaya) base64-embedded in app.py's CSS (data URI → zero cold-start
  requests, works on HF unchanged); CDU unit photo (FrankvEck) + "choice at a
  glance" stat card in section 03. Both CC BY-SA 4.0; credits inline +
  `docs/assets/credited/CREDITS.md` + provenance row 3b; Space assembly ships
  them. ⚠️ Commons discipline: NEVER hand-build upload.wikimedia URLs (hash
  paths — got a 135-byte 404 page); always fetch via the Commons API
  `prop=imageinfo` `iiprop=url|extmetadata` (also returns author/license).
  Original 13.85 MB hero downscaled via PIL to 1600px/356 KB q80.
- **marimo collisions round 2:** `base64`/`Path` defined in 3 cells after the
  imagery work → underscore-aliased per cell (`_base64`/`_Path`,
  `_cbase64`/`_cPath`). Every new cell must alias stdlib imports uniquely.
- **Skew-protection gotcha (the "Run failed" mystery):** marimo middleware
  rejects UI events from tabs whose server token doesn't match — after ANY
  server restart, open tabs get "Failed to update value" on click. Log line:
  `middleware:160 … invalid server token`. Remedy = tab refresh; NOT a code
  bug (verified 3× fresh-session green: DE $15.84, LP $15.67, feasible).
- **UI backlog for next session (user explicitly open to suggestions):**
  dark-restyle the matplotlib fan/tornado PNGs (white plates = the last
  visual mismatch), spinner UX on Run (~8–15 s silent), responsive pass,
  a11y audit (skills: ui-geometry-audit, web-design-guidelines), optional
  waterfall/count-up flourishes.

## Session Handover (2026-09-23e) — dashboard redesign (control-room console)
- **Design system shipped** (`app/app.py`): dark warm-graphite console
  (bg #0f0d0b, amber crude accents, Barlow Condensed + IBM Plex Mono via
  Google Fonts, async-load safe), KPI tiles, numbered section banners
  (01–06 + ▶ result) with "what you're looking at" captions, START-here
  stepper, dark Plotly template (`pio.templates['console']`), how-to-read
  callouts, ticker legend, waiting-prompt card. Directional-first per user
  brief. One `<style>` cell injected via `mo.Html` (plain string — CSS
  braces break f-strings).
- **marimo shell theming gotchas (cost 3 probe cycles — record!):** the
  white is painted by (1) `.bg-background` Tailwind token (gutters) and
  (2) EACH `.marimo-cell` wrapper (white under content). Override both with
  `!important`; find painters via `document.elementsFromPoint(x,y)` eval,
  verify with screenshot pixel probes (PIL), never via guessed selectors.
- **Lint:** `app/app.py` gets per-file-ignores E501 in pyproject (HTML/URL
  lines); `marimo check` now FULLY clean (HTML cells ended the
  markdown-indentation warning pattern). ⚠️ `git add -A` swept in
  `.playwright-cli/` + `output/` once — both now gitignored; browser-
  verification artifacts stay untracked.
- **Verified:** all-shell pixel probe dark=True, 137 tests, ruff, marimo
  check 0 issues, Space assembly green. Local preview: `uv run marimo run
  app/app.py` (user's browser session on port 2718 was live).

## Session Handover (2026-09-23d) — deploy pipeline + Phase 7 drafts
- **Space assembly pipeline DONE:** `scripts/build_space_root.py` →
  `deploy/space_root/` (gitignored build artifact, 38 files: app.py, src/,
  data/derived slices, risk PNGs, requirements/Dockerfile/README) with
  hard-fail assertions: no `.env`, no `*.pkl`, artifact completeness, marimo
  CVE floor, **pin-vs-lock drift guard**. ⚠️ Two real catches: (1) pins were
  derived from `uv pip list` — the venv had drifted ahead of uv.lock
  (numpy 2.5.3 vs 2.4.6, scipy 1.18.1 vs 1.17.1); pins now generated from
  uv.lock (one-liner in deploy/README.md); (2) **Space simulation** (headless
  export inside space_root with dangote-opt uninstalled) failed on
  ModuleNotFoundError — the template Dockerfile never installs the app's own
  package → documented one-line fix `ENV PYTHONPATH=/app/src` in
  deploy/Dockerfile. Simulation now passes = the exact image condition
  verified end to end.
- **User-side remaining (Step 18 item 2):** `deploy/hf-push-runbook.md` has
  the exact commands (create Docker Space → run script → push space_root →
  cold-start gate <2 s). Item 4 content ready: `deploy/portfolio/README.md`.
- **Phase 7 STARTED (Step 19):** `docs/executive-summary.md` (answer-first,
  headline table, risk framing, non-goals) + `docs/blog-post.md` ("The
  honest optimizer" — DE=LP as the hook) are publication-ready drafts;
  talking points + video remain; blog platform still open (spec §8).

## Session Handover (2026-09-23b) — Phase 6: ticker + deploy prep
- **Ticker DONE:** see HANDOFF item 3 above for the full detail (module,
  facets, snapshot, tests). Key files: `src/dangote_opt/data/ticker.py`,
  `scripts/refresh_ticker_snapshot.py`, app cell between the Phase 5 summary
  and transparency footer, `tests/test_ticker.py` (10 tests, injectable
  transports, zero network).
- **Deploy kit DONE (`deploy/`):** Space `requirements.txt` (marimo==0.24.2
  + exact numpy/pandas/pyarrow/scipy/scikit-learn/python-dotenv; joblib/
  matplotlib/plotly/requests arrive transitively), template-verbatim
  `Dockerfile`, `README.md` checklist. **User actions remain:** create the
  Docker Space, push `app.py` + `src/` + `data/derived/` + the two deploy
  files to the Space root, verify cold start <2 s, optionally add
  `EIA_API_KEY` as a Space secret for live WTI.
- **Docs updated same-commit:** provenance row 8 ✅ (FX + WTI verification
  detail), CHANGELOG (ticker + deploy kit), setup-steps Step 18 items 2/3.
- **Next up:** Step 18 item 2 user-side execution (HF account), then item 4
  (HF Static portfolio page). Phase 7 write-ups follow Phase 6.

## Session Handover (2026-09-19h) — Phase 5 session
- **Phase 5 DONE (2026-09-19h):** `optimization/scenarios.py` — 10k-draw Monte Carlo, **historical block bootstrap** (blocks of 12 consecutive months of EIA Δlog Brent+USGC, 2015–2025 — the brief's "what distribution / correlated shocks?" answered empirically; FX/demand = documented out-of-scope, USD price-taker). Per-draw **LP re-solve** via the Phase 4 skeleton (`build_lp_problem`/`solve_lp` — constraints price-independent, only `c` moves; ~8.5 ms/draw, 85 s total). ⚠️ Brent linkage: additive Δ = Brent_ref·(f−1) **cancels from the LP argmax** (Σx=1) — subtract from margin, never add to LP costs (differentials preserved). Results (`data/derived/scenarios_phase5.json`, seed 20260919): mean $17.68 ± 8.29, **VaR5 $6.25 / CVaR5 $1.42 / P(loss) 0.8%**; fixed-blend CVaR5 **−$3.50** → **re-opt worth +$2.56/bbl AND de-risks the tail**; two-regime diet ANS 50.5% / Forcados 47.9%. Fan + tornado figures in `docs/assets/`; app renders the precomputed summary (underscore-imports `_json`/`_Path` — marimo multi-cell collision workaround). `acquire.load_cached_series` = sidecar-located offline cache read (⚠️ cache-key reconstruction drifts when fetch params change — don't reconstruct). **127 tests.**
- **Next up: Phase 6** — dashboard & deploy: marimo app → HF Spaces (pin CVE-2026-39987-patched marimo release first, spec open item 5); deep re-opt UX now trivially inside budget (~3 s); precomputed artifacts render instantly on cold start.
- **Also open:** verify driver on *real* Colab (optional); OPEC MOMR differential refresh; notebook polish (marimo narrative per phase — spec decision 12).
- **Session Handover (2026-09-19g) — Phase 4 session:**
- **Phase 4 DONE (2026-09-19g):** `optimization/de_driver.py` (vectorized DE over `objective.batch_call`, Sobol init, convergence history captured via the `intermediate_result` callback — scipy inspects the signature, don't re-guess) + `optimization/baselines.py` (equal-weight · random search 10k batched · **exact LP**: the bridge is affine in severity, `u_j = s·x_j` linearizes it, quality specs are hard linear constraints from the same `BatchQualityModel` coefficients as the DE penalty). **Structural finding: DE ≡ LP to <0.5¢/bbl** — the physics are linear in the decision vars (methodology §6a); the honest bar is met exactly. **Speed: 0.85 s/bridge run, ~3.4 s/ETR run (was 127 s)** — 30–60 s budget has ~20× headroom. 100-seed sweep committed (`data/derived/sensitivity_phase4.json`, mean $15.84 ± 0.00, uplift +11.3%) + figures in `docs/assets/`. Batch paths exact to machine eps (`bridge.blend_yields_batch`, `quality.BatchQualityModel` — pinned in `tests/test_phase4.py`; ⚠️ don't double-square the quality violation: `violation_magnitude` already applies the LQ form). scipy vectorized DE passes populations **(n_vars, S)** — `batch_call` normalizes axes. **121 tests.** Note: through the surrogate, DE lands ~1% above the bridge-LP bar ($15.84 vs $15.67) = surrogate model error, disclosed.
- **Next up: Phase 5** — scenario analysis (Monte Carlo 10k as briefed, **3-scenario bull/base/bear mini is the pre-agreed descope fallback** — decide by workload); reuses the batch paths (10k draws ≈ one vectorized pass) so the full Monte Carlo is now cheap.
- **Also open:** verify driver on *real* Colab (optional); Phase 6 dashboard polish (marimo pin + CVE check at kickoff, spec open item 5); OPEC MOMR differential refresh.
- **Buffer-week decision (spec §8 item 7, made at Phase 3 exit):** Phases 1–4 all landed early/inside budget — the buffer week goes to **Phase 4 hardening + Phase 5 head start** (sensitivity sweep already delivered the Phase 4 deliverable early); if Phase 5's Monte Carlo is cheap enough via batch paths (it is — minutes), trigger the **full 10k MC instead of the 3-scenario fallback**.

## Session Handover (2026-09-19f) — Phase 3 session
- **Phase 3 DONE (2026-09-19f):** ETR surrogate behind the existing hooks — `models/dataset.py` (Dirichlet α=0.55 simplex × U(0,1) severity, seed 20260919; features = blend-weighted properties **+ blend-weighted TBP cut fractions** = the bridge's actual inputs) · `models/train_surrogate.py` (ETR 150×14×4 — 300 trees hit 96.5 MB, violates the 50 MB hosting guard, don't re-tune; dual CV per spec §3.5, self-written permutation importance — sklearn's scorer chokes on multi-output, don't re-try). **Results in `models/model_card.md` (committed):** random 5-fold min R² = **0.982** (impressive gate >0.90 passed); leave-crude-out — gasoline 0.93 / diesel 0.78 / petrochem 0.97, **jet collapses to ≈0.11** (honesty finding: the ANS fold tests below the training range and trees can't extrapolate; quantified in the card; deployment never needs unseen crudes). Fidelity: max |Δ| ≈ 0.0007 vs bridge in-envelope; DE optimum unchanged. pkl **gitignored** (deterministic, regenerates in ~5 s via `scripts/train_surrogate.py`); app loads pkl with bridge fallback; **114 tests**. ⚠️ Surrogate `predict` in the DE hot loop: use numpy feature rows, never per-call DataFrame + threadpool spawn (made the app smoke time out at 300 s; fixed). ⚠️ **Provenance row 7 superseded:** the MIT ML-PSE FCCU dataset is fault-detection data (NOC envelope + equipment faults, controllers active) — **no severity sweep**, cannot calibrate yield-vs-severity shape; probed `Plotall.m`/`dynamic.m`/FDD notebooks to confirm; bridge's cited G&H shape stands.
- **Next up: Phase 4** — buffer allocation (spec §8 item 7 — decide at Phase 3 exit, which is now); `optimization/de_driver.py` budget work if the app DE (~127 s with surrogate) misses the 30–60 s spec window.
- **Also open:** verify driver on *real* Colab (optional); Phase 5 dashboard polish; OPEC MOMR differential refresh (Phase 2+ task).

## Session Handover (2026-09-19b) — data-layer session
- **Done this session (Phase 1 data layer, code + live verification):** EIA v2 client (`data/acquire.py`: cache-first parquet + sidecars in `data/raw/eia/`, pagination w/ hard stop, `units` never coerced, injectable transport; route contract verified against official v2 guide) · assay records (`data/assays.py`: provenance-required, quality rules enforced at construction, `validate_slate()` = unique ids + exactly 5) · CrudeOilMix mapper (`data/crudeoilmix.py`: word-segment matching in `mix_json`, unknown keys surfaced, reject frame, whole-crude stream filter) · `scripts/eia_smoke.py` = live verification once key lands → then pin confirmed series IDs in provenance row 2 · **57 offline tests, ruff clean.**
- **EIA live-verified 2026-09-19 (key registered → `.env`, smoke run green):** catalog pinned — `petroleum/pri/spt` (USGC spot: `EPMRU` gas / `EPD2DXL0` ULSD / `EPJK` jet, `RGC`/`PF4`, $/gal; `EPCWTI`/`EPCBRENT` also on route in $/bbl) · `petroleum/sum/snd` (`EPC0`+`YIR`+**`NUS`** — NOT `NUS-Z00`, it has 0 `YIR` rows) · `petroleum/move/impcus` (`EPC0`+`IM0`+`NUS-NNI` = Nigeria). `units` is NOT a valid `data[]` column (echoed per row). Real parquet + sidecars now in `data/raw/eia/`. ⚠️ SECURITY near-miss: key briefly pasted into committed `.env.example` — moved to gitignored `.env`, never staged/pushed. No Bonny Light spot on EIA → Brent anchor `EPCBRENT` + documented differential (provenance row 9).
- **Slate finalized (Phase 1 exit criterion met):** Bonny Light / Forcados (TotalEnergies sheets) + Qua Iboe / Alaska North Slope / Thunder Horse (ExxonMobil) — real published assays, validated, committed as `data/derived/slate_phase1.parquet` + sidecar. **Arab Light/Urals substituted — no open TBP assays exist** (ExxonMobil library checked; don't re-search). Parsers in `data/assay_parsers.py`; yield basis per crude in `notes` (TE=wt%, XOM=vol% grid — bridge must not mix). PDFs gitignored in `data/raw/assays/` (vendor docs, not redistributed). Assay validation now also enforces cumulative-yield monotonicity.
- **Phase 2 Stage-1 bridge DONE (2026-09-19c):** `features/bridge.py` — cut scheme <180/180-260/260-360/360-540/>540 °C; FCC conversion 40→80% of VGO linear in severity (Gary & Handwerk cited range), splits gas 50%/LCO 18%/gas+coke 32%; HT loss 1% on diesel (ICCT ex.17); curves stored **vol% uniform** (TE parser fixed: vol column, gas-in-curve simplification ≈2 vol% documented). **Ground-truthed:** parsed-curve cuts vs published Bonny Light table ±0.2 vol% (§5 of methodology.md). `docs/methodology.md` cites every constant; Maples correlations reviewed & rejected (not openly reproducible — don't re-litigate). Objective has `yield_model` hook = Phase 3 ETR signature; app now runs REAL slate + bridge yields (costs still placeholder). 73 tests.
- **Cost anchor DONE (2026-09-19d, provenance row 9 ✅):** `brent_spot` in the EIA catalog (product `EPCBRENT`, duoarea **`ZEU`** — NOT `RGC`, probed live; series `RBRTE`, native $/bbl). `data/costs.py`: delivered cost = trailing-12m EIA Brent (**$69.10/bbl**, 132 cached monthly rows) + per-grade differential — every differential **ASSUMED** w/ documented quality rationale; refresh via OPEC MOMR actuals (Phase 2+). Ordering sanity tested (premium ~ API within sulfur class; sour discounts); strict KeyError on unknown grade — never silently default. Committed `data/derived/costs_phase2.parquet` + sidecar (`scripts/build_costs.py`). App runs real slate + real costs (footer discloses ASSUMED differentials). Result with real economics: DE blends 47% Forcados + 52% ANS (sour discount vs sweetening trade-off) at $21.47/bbl vs $20.05 equal-weight. 82 tests. Product prices remain placeholder — wiring the EIA USGC series into the objective is the last Phase 2 economics item.
- **Quality specs + real product prices DONE (2026-09-19e) — Phase 2 complete:** `features/quality.py` (RON linear / RVP psi^1.25 index per Haverly / freeze / cetane linear; unit-output qualities cited in methodology §3c; per-crude component qualities PUBLISHED for TE crudes, ASSUMED-mid for XOM — XOM's RON row is unusable in extraction, MON > RON under every alignment, don't re-try). Bridge gained **octane units** (§3b): isom/reformer-85%/alkylate-50%/butane-pull-25% — required or RON 91 is infeasible (SR naphtha ≈ 58); `component_volumes()` = one mass balance behind yields AND quality (equivalence pinned in tests). Objective has `quality_model` hook (same injectable pattern as `yield_model`). Prices: `data/prices.py` wires EIA USGC (EPMRU/EPD2DXL0/EPJK, ×42, 12-mo avg) into the objective; **petrochem price = disclosed PLACEHOLDER** (no citable EIA spot for LPG/propylene/residue basket — probed `pri/resid`, `pri/refoth`, naphtha codes; refresh path in prices.py). App DE now lands ~98% ANS @ sev 1.0 with RON 91.4 / cetane 45.1 nearly binding — quality specs have real teeth. **102 tests.**
- **Next up: Phase 3** — ETR surrogate (features/surrogate.py) trained on bridge-generated labels (the `yield_model`/`quality_model` hooks are the plug-in signatures); dual CV (random 5-fold + leave-crude-out GroupKFold); FCCU dataset for severity-shape calibration (provenance row 7).
- **Also open:** verify driver on *real* Colab (optional); FCC correlation set at Phase 2 kickoff (spec §8 item 2); Phase 4 buffer allocation at Phase 3 exit (§8 item 7).
- **Do not re-litigate:** marimo (not Streamlit), all-in on marimo notebooks, 5 crudes/4 products/single period, DE baselines incl. LP, dual CV, uv tooling, public repo, Colab optional-only, project stays on D:.

## Session Handover (2026-09-18, rev. 2026-09-19) — plan audit
- **Done this session (plan-vs-repo audit + fixes):** app bug fixed — the result cell rendered *nothing* after Run because `mo.md()` sat inside `if run.value:` (marimo only displays a cell's last top-level expression); rewritten with `mo.stop()`, severity slider now drives the equal-weight baseline severity (spec §3.4) · constraint handling added to `RefineryObjective.__call__`: linear+quadratic penalty (`CONFIG.constraint_penalty = 10_000`) for API-window/sulfur-cap violations, plus `margin()` (unpenalized, what the app reports) / `violation_magnitude()` / `blend_properties()` (reuses features/blend.py) · placeholder yields now **blend-aware** (API→light products, S→distillate loss) so DE has a real trade-off — it still picks 100% Urals\* on the mock slate, but legitimately ($7.04 vs $1.15 eq-weight; margins are illustrative until Phase 2) · `datasets` declared dep, driver no longer pip-installs, probe cell ordered after install via DAG dep · `.gitignore` blanket `*.parquet` removed (derived slices go in `data/derived/`) · spec F2/F8/§2.4 annotated for the marimo decision + verified Electric Sheep schema; Phase 4 one-week-vs-scope compression logged as **open item 7** · **22 tests, commit 5f4c25c pushed, CI green** (run 35413685351).
- **Next up (Phase 1, in order):** ① register EIA API key → `.env` (**user action, only blocker**) · ② implement `src/dangote_opt/data/acquire.py` (EIA client w/ parquet caching, assay parsers) · ③ write `mix_json` schema mapper for CrudeOilMix · ④ finalize 5-crude slate from public assays (spec §8 item 1).
- **Also open:** verify driver on *real* Colab (optional — WSL test already covers the pattern); FCC correlation set choice at Phase 2 kickoff (spec §8 item 2); Phase 4 buffer allocation at Phase 3 exit (spec §8 item 7).
- **Do not re-litigate:** marimo (not Streamlit), all-in on marimo notebooks, 5 crudes/4 products/single period, DE baselines incl. LP, dual CV, uv tooling, public repo, Colab optional-only, project stays on D:.

## What This Project Is
ML surrogate model (Extremely Randomized Trees) + Differential Evolution optimization for **Dangote Refinery (650,000 bpd)** crude-blend and FCC-severity planning. Goal: maximize refinery margin (product value − crude cost) subject to blend/capacity/quality constraints.

- **Type:** Portfolio project (methodology demonstration) — NOT a real Dangote system, no proprietary/NDA data.
- **Status:** Phase 0 complete — repo scaffolded, committed, and public: https://github.com/batestguy/dangote-refinery-optimizer (CI green, 22 tests passing). Implemented: config, blend math, margin objective + simplex repair + constraint penalty, blend-aware placeholder yield model, marimo app POC. Stubs awaiting phases: data acquisition (P1), TBP→yields bridge (P2), ETR surrogate (P3), DE driver + baselines (P4), dashboard polish (P6).
- **Governing docs:** `plan-improvement-spec.md` (all locked decisions §4 — read before changing scope) + `docs/setup-steps.md` (execution record) + `docs/problem_statement.md` (formulation) + `docs/data_provenance.md` (verified sources).

## Stack (Python 3.12, uv-managed)
- **Data:** pandas, NumPy, PyArrow (Parquet); HuggingFace `datasets` (streaming only), requests
- **ML:** scikit-learn (ETR primary), XGBoost/LightGBM (comparison); SHAP (Phase 3)
- **Optimization:** SciPy `differential_evolution`
- **App/Notebooks:** **marimo** for both (decided 2026-09-18, replacing Streamlit/Jupyter; Streamlit = documented ≤2-day fallback since all logic lives in src/)
- **Test/Lint:** pytest + ruff | **Env:** uv + pyproject.toml, `uv.lock` committed

## Commands
```bash
uv sync                        # install deps (uv manages Python 3.12; system 3.14 not used)
uv run pytest                  # tests
uv run ruff check .            # lint (CI runs both)
uv run marimo run app/app.py   # app locally; same file deploys to HF Spaces
# Colab (free tier): notebooks/00_free_tier_driver.py — clone → pip install -e . → probes
```

## Key Data Sources
- `anon12-neurips-2026/CrudeOilMix` (HF, CC-BY-4.0) — verified: 1,141,933 simulator-generated blend samples from 9,061 real assays; **stream, never bulk-download**
- `electricsheepafrica/*` (HF, MIT — **synthetic**): pricing CSV is only 27 rows (useless for economics — EIA-anchored instead); refineries dataset used for Dangote metadata only
- EIA Open Data API v2 — free key in `.env` (see `.env.example`); cache pulls to `data/raw/` parquet
- Public assays (ExxonMobil/TotalEnergies/Equinor/NUPRC) for the 5-crude slate — Phase 1
- FCCU dataset (mlforpse.com) — yield-vs-severity *shape* calibration — Phase 2

## Conventions & Gotchas
- **Transparency rule:** synthetic/placeholder inputs are marked `*` in the app and labeled in `docs/data_provenance.md`; never present outputs as real Dangote operations.
- **Scope guard:** 4 products, 5 crudes, single period; decisions change via the spec, not ad-hoc.
- Linear blending for API/sulfur (implemented in `features/blend.py`); quality-spec LBIs (RON, cetane, RVP) come as Phase 2 constraints.
- Dual CV in Phase 3: random 5-fold (headline) + leave-crude-out GroupKFold (honesty) — always report both.
- Baseline contract: DE always reported vs equal-weight + random + LP (spec §3.4).
- **marimo gotchas:** a cell renders only its last *top-level* expression — a `mo.md()` inside `if ...:` shows nothing; use `mo.stop(cond, fallback_output)` then end the cell with the output (this bug shipped in the Phase 0 app and was fixed 2026-09-19). Source order ≠ execution order: a cell that needs another's side effect (e.g. Colab install) must reference one of its variables. `datasets` is a declared dependency — never `pip install` from a notebook.
- **Windows gotchas:** uv picked a broken LibreOffice Python — fixed via `uv python install 3.12` + `.python-version`; console is cp1252 — prefix marimo CLI with `PYTHONUTF8=1` when output has emoji; use POSIX bash syntax.
- **Git artifacts rule:** `data/raw/` and `data/processed/` are gitignored; small derived slices go under `data/derived/` and ARE committed (no blanket `*.parquet` ignore).
- **Storage decision (user-locked 2026-09-18, verified same day):** project stays on `D:\Dangote`. Verified facts: D: is a USB external drive ("Generic External USB Device") — NOT an SSD (cold-file read 39 MB/s on a file untouched since Mar 2025; write 35 MB/s; small-file create 322/s; the only SSD is C:'s Samsung MZNLN256HAJQ). USB enclosures hide the media flag, so identity queries are inconclusive — trust the cold-read benchmark. Earlier "reads ≈ equal" claim was RAM-cache artifact, now corrected. Accepted trade-off: cold reads + installs + git commits are slow; mitigate by keeping working parquet slices small. uv cache is on C: (default `%LOCALAPPDATA%`). No D: backup — GitHub is the sole git backup. C: migration offer stands (~10 min) if this ever hurts.
- Deployment (Phase 6): HF Space via `marimo-team/marimo-app-template` fork; sleeps ~48 h → pre-computed fallback must render instantly; pin CVE-2026-39987-patched marimo; no upload/code-exec widgets.
- Free-tier discipline: GitHub Actions + HF Space + Colab + EIA key + streaming HF datasets — nothing paid, ledger in `docs/setup-steps.md`.
