# Project knowledge

Orientation for any agent (or human) joining this repo. Session-by-session
detail lives in [`knowledge.md`](knowledge.md); the governing spec is
[`plan-improvement-spec.md`](plan-improvement-spec.md).

## What this project is

ML surrogate (ETR) + differential evolution for crude-blend / FCC-severity
optimization at a 650 kbpd refinery — a **methodology demo on free/open data
only** (no Dangote affiliation, no proprietary data). **Phases 0–5 are
complete** (slate → bridge → surrogate → optimization → scenario risk).
Remaining: **Phase 6** (marimo pin + HF Spaces deploy + FX/WTI ticker) and
**Phase 7** (write-ups). 127 offline tests, CI green on every push.

## Commands

```bash
uv sync                                   # install (uv.lock committed — reproducible)
uv run pytest                             # 127 tests, fully offline, ~15 s
uv run ruff check . && uv run ruff format .   # lint + format (CI parity)
uv run marimo check app/app.py            # app structure check (1 cosmetic warning is pre-existing)
uv run marimo run app/app.py              # the app locally
PYTHONUTF8=1 uv run python scripts/train_surrogate.py     # ~5 s, deterministic → models/etr_surrogate.pkl (gitignored)
PYTHONUTF8=1 uv run python scripts/sensitivity_study.py   # 100 DE seeds (~6 min) → figures + JSON
PYTHONUTF8=1 uv run python scripts/run_scenarios.py       # 10k Monte Carlo (~85 s) → figures + JSON
```

Set `PYTHONUTF8=1` for any command that prints Unicode (Windows console).
Live EIA pulls need `EIA_API_KEY` in `.env` (gitignored); everything else runs
from committed `data/derived/` artifacts.

## Architecture (data → decision flow)

1. **Assays** (`data/assay_parsers.py` → `data/assays.py`): two vendor PDF
   formats → validated `AssayRecord`s (API, sulfur, TBP curve on a uniform
   vol% basis) → committed slate `data/derived/slate_phase1.parquet`.
2. **Bridge** (`features/bridge.py`): TBP cut-point integration + cited FCC
   conversion/splits + octane units → 4-pool yields. `blend_yields_batch` is
   the exact vectorized path. Ground-truthed to ±0.2 vol% vs published cut
   tables (`docs/methodology.md` §5).
3. **Quality** (`features/quality.py`): pool qualities (RON/RVP/freeze/cetane)
   from the bridge's component streams (`component_volumes()` — one mass
   balance, two consumers). `BatchQualityModel` is the exact batch mirror.
4. **Surrogate** (`models/`): ETR learns the bridge (features = blend-weighted
   properties + TBP cuts). Dual CV in `models/model_card.md`. Deterministic;
   pkl is gitignored and regenerates in ~5 s.
5. **Objective** (`optimization/objective.py`): margin − penalties, with four
   injectable hooks: `yield_model`, `quality_model`, `batch_yields`,
   `batch_quality`. Batch paths ≡ scalar paths (pinned to machine precision).
6. **Optimization** (`optimization/de_driver.py`, `baselines.py`): vectorized
   DE + mandatory 3-way baselines. The LP is *exact* (`u_j = s·x_j`
   substitution — the physics are affine in severity).
7. **Scenarios** (`optimization/scenarios.py`): block-bootstrap Monte Carlo,
   per-draw LP re-solve, VaR/CVaR, tornado.

## Conventions

- **Traceability rule:** every number is (a) integrated from a published curve,
  (b) cited with a source, or (c) labeled ASSUMED/PLACEHOLDER with a rationale
  and refresh path. Nothing invented silently — `docs/methodology.md` is the
  audit trail.
- **Dual CV discipline:** always report random 5-fold AND leave-crude-out,
  never one alone.
- **Test before trust:** batch paths, mass balances, and physical invariants
  are pinned by tests; equivalence claims live in `tests/`.
- Docs update in the same commit as the code they describe (CHANGELOG,
  methodology, provenance, `docs/setup-steps.md` execution record).
- Commit style: imperative subject + body explaining the *why*; Codebuff footer.
- Windows/bash quirks: forward slashes, `PYTHONUTF8=1`, check exit codes —
  never trust the last line of piped output (`tail -1` has masked failures).

## Things to avoid (settled — do not re-litigate)

- marimo, not Streamlit (app + all notebooks). All-in on marimo.
- Maples FCC correlations: rejected for traceability; don't re-search.
- MIT ML-PSE FCCU dataset: fault-detection data, no severity sweep — cannot
  calibrate yield-vs-severity (provenance row 7 superseded).
- Arab Light / Urals: no open TBP assays exist; slate substitution is final.
- Model size: 150×14×4 ETR is final (300 trees = 96.5 MB > 50 MB HF guard).
- XOM light-naphtha RON row: unusable in PDF extraction (MON > RON under every
  alignment); those values stay ASSUMED.
- Never commit `.env`, `data/raw/`, `models/*.pkl`. Sidecars must not contain
  the API key (verify before committing).
- scipy vectorized DE passes populations as **(n_vars, S)** — `batch_call`
  normalizes axes; the DE callback must take `intermediate_result` (scipy
  inspects the signature).
- Don't double-square quality violations: `BatchQualityModel.violation_magnitude`
  already applies the linear+quadratic form once.
- Brent scenario shocks: the additive cost shift cancels from the LP argmax —
  subtract Δ from margins, never add shifted costs into the LP.
- Offline cache reads: use `acquire.load_cached_series` (sidecar-located) —
  cache-key reconstruction drifts when fetch params change.

## Gotchas that cost real time (recorded so they don't again)

- 0-row EIA caches are *valid* API behavior (wrong facet guess), not errors —
  the Brent duoarea is `ZEU`, not `RGC`.
- Vendor TBP tables include ~2.1 vol% dissolved C2–C4 in the first row; the
  documented simplification (gas stays in the curve) explains the only
  ground-truth gap.
- sklearn's `permutation_importance` cannot score a multi-output regressor
  against single-target y — the self-contained loop in
  `train_surrogate.permutation_importances` is deliberate.
- marimo: a cell's last top-level expression is the output (use `mo.stop()` for
  conditional rendering); variables must be unique across cells (underscore-
  prefix colliding imports, e.g. `_json`/`_Path`).
