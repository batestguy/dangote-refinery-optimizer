# Data Provenance

**Status:** skeleton (Phase 0). One row per input; every cell in the app/model must trace here. Rule: **real vs synthetic is labeled wherever data is displayed** (spec §4 decision 7, §6 risk).

## Verified sources

| # | Source | What we use | Access | License | Verified | Notes |
|---|--------|-------------|--------|---------|----------|-------|
| 1 | `anon12-neurips-2026/CrudeOilMix` (HF) | whole-crude assay properties, blend properties, TBP curves | `load_dataset(..., streaming=True)` — **no bulk download** (minimal-first, spec §4 row 6) | CC-BY-4.0 | ✅ 2026-09-18 via HF API: 1,141,933 simulator-generated samples from 9,061 real assays (H/CAMS); parquet. ✅ streaming verified from WSL/Linux: top-level columns are `oilid, n_components, is_blend, mix_json` — **assay detail is nested in `mix_json`**, schema mapping is a Phase 1 task | Simulator-generated *labels*; real *assay* inputs. Not unit yields — feeds Stage-1 bridge, not the surrogate directly |
| 2 | EIA Open Data v2 | product prices (gasoline/diesel/jet), refinery utilization, crack-spread proxies | REST, free key (`.env`, `EIA_API_KEY`) | public | 🔜 Phase 1 | Cache every pull to `data/raw/` parquet; record series IDs here |
| 3 | ExxonMobil / TotalEnergies / Equinor crude assays | per-crude (API, sulfur, TBP) for the 5-crude slate | public web | public | 🔜 Phase 1 (parse + verify each) | Candidates: Bonny Light, Forcados, Qua Iboe + 2 global grades (spec §8 open item 1) |
| 4 | NUPRC / NNPC publications | Nigerian crude quality spot-checks | public, partial | public | 🔜 Phase 1 | Cross-check vendor assays |
| 5 | `electricsheepafrica/africa-synth-energy-oilgas-crude-pricing-nigeria` (HF) | **annual Nigerian crude-grade prices** (Bonny Light, Forcados, Qua Iboe, Brass River, Escravos) + Brent + spreads-to-Brent + data-quality flags | HF datasets, streaming | MIT | ✅ 2026-09-18: **27 rows / 3.59 kB = annual series 1999–2025** (verified keys: `year, brent_crude_usd_per_bbl, bonny_light_usd_per_bbl, …, bonny_light_spread_to_brent, data_source, data_quality`). Too coarse for product prices, but usable as a crude-cost anchor | SYNTHETIC — labeled wherever displayed; **no product prices** (gasoline/diesel/jet still come from EIA, row 2) |
| 6 | `electricsheepafrica/africa-synth-energy-oilgas-refineries-nigeria` (HF) | Dangote metadata (650 kbpd, utilization ~0.8) | HF datasets | MIT | 🔜 Phase 1 | SYNTHETIC — labeled wherever shown |
| 7 | FCCU operational dataset (mlforpse.com) | yield-vs-severity *shape* calibration for Stage 2 | download | open | 🔜 Phase 2 | No linkage to assay slate — used for response shape only |
| 8 | open.er-api.com | NGN/USD FX for dashboard ticker | REST, no key | fair use | 🔜 Phase 6 | Cache 1 h |
| 9 | Bonny Light / Forcados spot | crude cost anchor | public spot series / Brent-minus-differential convention | public | 🔜 Phase 1 | Any assumed differential is documented right here |

## App placeholder disclosure

`app/app.py` slate (names, APIs, sulfurs, costs marked `*`) is **illustrative placeholder** until rows 3/9 land in Phase 1. Prices come from `CONFIG.default_prices` until row 2 lands.

## Data quality rules (Phase 1 exit criteria)

- Every assay record: (api, sulfur_pct, tbp_curve) complete or explicitly imputed-with-documented-default.
- Unit sanity: API in [10, 50], sulfur in [0, 5] wt-%, TBP monotonic 0–100%.
- Pull dates + URLs recorded per artifact in `data/raw/` sidecar JSON.
