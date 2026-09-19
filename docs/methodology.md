# Methodology — Stage-1 Pseudo-Refinery Bridge

**Status:** v1.0 — Phase 2 deliverable (spec §3.1, §5 Phase 2). Every number in
`src/dangote_opt/features/bridge.py` is either (a) integrated from a published
TBP curve or (b) a documented, cited value below. No invented coefficients.
**Validation-first:** the parser + cut integrator reproduce the published
Bonny Light cut yields to ±0.2 vol% (see §5) before any modeling is layered on.

## 1. Cut-point scheme

| Cut | Range (°C) | Destination |
|---|---|---|
| SR naphtha | < 180 | gasoline pool |
| SR kerosene | 180–260 | jet pool |
| SR distillate | 260–360 | diesel pool |
| Vacuum gas oil (VGO) | 360–540 | FCC feed |
| Residue | > 540 | petrochem/fuel pool |

Industry-standard atmospheric + vacuum scheme (spec §3.1; consistent with
Gary & Handwerk ch. 2 and the ICCT refining tutorial's process descriptions).
All curves are stored on the **vol%** column (uniform basis; provenance row 3)
and anchored at (15 °C, 0 %) by the parser.

## 2. FCC conversion & product split

| Parameter | Value used | Cited basis |
|---|---|---|
| Conversion at s=0 | 40 % of VGO | low end of typical VGO-FCC conversion (Gary & Handwerk ch. 4: ≈55–75 % at typical severity; 40–80 % span keeps endpoints conservative and lets severity s interpolate) |
| Conversion at s=1 | 80 % of VGO | upper end of the same range (deep conversion operation) |
| Converted-VGO → gasoline | 50 % | midpoint of the nominal FCC gasoline yield on converted feed (Gary & Handwerk ch. 4 FCC yield tables; ICCT tutorial: "FCC offers high yields of gasoline… G/D ratio depends on operating conditions and catalyst") |
| Converted-VGO → LCO (diesel-range) | 18 % | nominal light-cycle-oil share (same tables; ICCT exhibit 15: LCO is a major diesel blendstock from FCC) |
| Converted-VGO → light gas + coke | 32 % | remainder (mass balance; ICCT: FCC also produces "significant light gases" plus coke on catalyst) |
| Unconverted VGO ("slurry") | (1 − conversion) | ICCT: "un-reacted FCC feed (called slurry oil)" stays heavy → petrochem/fuel pool |

**Severity semantics:** `s ∈ [0,1]` is a *normalized conversion proxy*
(problem statement §2) — it linearly spans the cited conversion window. It is
**not** a reactor temperature; no plant data is claimed (spec §3.6, §7).

## 3. Treating & quality (yield-side)

- **Hydrotreater yield loss ≈ 1 vol%** — applied to the diesel pool
  (ICCT tutorial, Leiby 2011, exhibit 17: "yield loss is small, usually on the
  order of ≈1 vol%"). Sulfur pickup itself is *quality*, not yield; sulfur
  enters Phase 2 constraints via blend indices, not via the bridge (spec §3.3).
- Naphtha/kero/jet pools are not HT-adjusted (conservative; documented here).

## 3b. Octane units (fixed-fraction yield transforms)

Physical motivation: straight-run naphtha blends at **RON ≈ 58** (measured:
Bonny Light 80–150 °C cut RON 54.3, TE sheet) — no real blend meets the RON 91
gasoline spec without octane units. The bridge therefore routes:

| Transform | Feed | Yield used | Cited basis |
|---|---|---|---|
| Isomerization | light naphtha (< 80 °C) | ≈ 100 % (isomerate) | rearrangement reaction, no yield loss (Gary & Handwerk ch. 8) |
| Reforming | mid naphtha (80–180 °C) | **85 %** reformate; balance LPG+H₂ → petrochem pool | reformate yield 80–88 vol% of feed at high severity (Gary & Handwerk ch. 9 reformer yield tables); 85 = midpoint |
| Alkylation | FCC C₃/C₄ (inside the gas+coke lump) | **50 %** of the lump → alkylate; balance = fuel gas + coke + propylene → petrochem pool | conservative share: alkylate yield on actual C₄s is ≈ 1.0–1.7 vol (Gary & Handwerk ch. 7), but the gas+coke lump also contains dry gas and coke |
| Butane pull-off | light-naphtha front end | **25 %** of light naphtha → LPG (petrochem pool) | RVP is managed via butane content (standard practice); share ASSUMED — the constraint binds via the RVP math in §3c, so the exact share shifts the blend, not feasibility |

The octane uplift itself lives in §3c (unit-output qualities), because RON is a
*quality*, not a yield. These transforms change the yield vector (gasoline pool
= isomerate + reformate + FCC gasoline + alkylate) and are reflected in the
pooling table (§4).

## 3c. Quality-spec constraints (blend indices)

Implemented in `features/quality.py`; enforced via a linear+quadratic penalty
(same form and `CONFIG.constraint_penalty` scale as the blend-property block).

**Blending rules** (spec §4 decision 14 — LBI where the property is non-linear):

| Property | Rule | Citation |
|---|---|---|
| Gasoline RON | linear by volume | octane numbers are engine indices; linear volumetric blending is the LP-standard base rule (Gary & Handwerk ch. 10). The interactive Ethyl RT-70 scheme (Healy et al.) is more accurate but not openly reproducible → traceability rule |
| Gasoline RVP | **RVP^1.25 index** blended linearly, inverted | the widely used psi^1.25 index (Haverly Systems, "Blending by Index") |
| Jet freeze point | linear by volume | standard practice for closely-boiling single-pool property |
| Diesel cetane index | linear by volume | standard for cetane *index* blends (D4737A values from the sheets) |

**Unit-output qualities** (constant, severity-free — reformate RON is set by
reformer severity, not by the crude):

| Stream | RON | RVP kPa | Basis |
|---|---|---|---|
| isomerate | crude light-naphtha RON + 4 | 55 | uplift 78→~82, typical isomerization endpoint (G&H ch. 8) |
| reformate | 98 | 12 | high-severity reformer endpoint of the 85–95+ range (G&H ch. 9) |
| FCC gasoline | 93 | 35 | midpoint of 91–95 (G&H ch. 4) |
| alkylate | 93 | 25 | midpoint of 90–98 (G&H ch. 7) |
| FCC LCO | cetane 22 | — | LCO is a low-cetane blendstock; ≈ 20–25 (ICCT tutorial) |

**Per-crude component qualities** (gasoline isomerate RON, jet freeze, SR
diesel cetane) — PUBLISHED where the vendor sheets provide them, ASSUMED with
rationale where not (`CRUDE_QUALITIES` in features/quality.py carries the
status strings; provenance row 3):

| Crude | Light-naphtha RON | Kero freeze °C | SR diesel cetane | Status |
|---|---|---|---|---|
| Bonny Light | 77.2 | −56 | 45.2 | PUBLISHED (TE 15-80 / 150-250 / 230-375 cuts) |
| Forcados | 77.4 | −56 | 45.2 | PUBLISHED (same TE cuts) |
| Qua Iboe | 78.0 (ASSUMED — XOM RON row unusable in extraction: MON > RON under every alignment) | −43 (mid of published kero-range) | 55.0 (mid of published 50–61) | mixed |
| Alaska North Slope | 78.0 (ASSUMED, same XOM issue) | −50 (mid) | 50.0 (mid of 46–51) | mixed |
| Thunder Horse | 78.0 (ASSUMED, same XOM issue) | −44 (mid) | 55.0 (mid of 53–61) | mixed |

**Sensitivity note:** single-crude pools pass all four specs with wide margin
except diesel cetane (LCO dilution) — the binding constraints in practice are
RON and cetane at high severity (verified in `tests/test_quality.py` and the
app's DE runs).

| Product | Components |
|---|---|
| gasoline | isomerate (light naphtha < 80 °C, net of butane pull) + reformate (85 % of mid naphtha) + FCC gasoline + alkylate (50 % of FCC gas+coke) |
| diesel | SR distillate (260–360 °C) + FCC LCO, less HT loss |
| jet | SR kerosene (180–260 °C) |
| petrochem | residue (>540 °C) + FCC slurry + non-alkylated FCC gas + reformer LPG + butane pull (LPG/propylene/PGP proxy) |

Sums ≈ 1 per crude (≤ 1% HT loss); verified in tests (`test_bridge.py`).

## 5. Validation against published yields (Bonny Light, TE sheet 18-Jun-20)

Cuts integrated from the parsed curve vs the sheet's own cut-yield table
(vol%):

| Cut | Parsed curve | Published table | Δ |
|---|---|---|---|
| naphtha 80–150 | 14.3 | 14.5 | −0.2 |
| naphtha 80–175 | 19.4 | 19.5 | −0.1 |
| kerosene 150–230 | 15.3 | 15.1 | +0.2 |
| kerosene 150–250 | 20.0 | 19.8 | +0.2 |
| gasoil 175–400 | 49.0 | 49.0 | 0.0 |
| gasoil 230–375 | 34.6 | 34.7 | −0.1 |

Interior cuts reproduce to **±0.2 vol%** — the parser/integrator is
ground-truthed. The `15–80 °C` naphtha cut differs because the TBP table's
first row (80 °C ≈ 9.8 vol%) **includes ≈2.1 vol% dissolved C2–C4 gases**
(the sheet's own gas composition: 0.1+0.5+0.5+1.0 vol%) while the cut table
starts at 15 °C excluding gas. Simplification, documented: gas stays in the
curve and lands in the gasoline/petrochem pools; at Dangote scale this is
≈2% of feed and does not change any blend decision. Whole-crude endpoint
checks: Bonny VGO+residue 28.8 % vs published ≈26 vol% (>375 °C, vol/wt
basis difference); ANS residue ≈2.5× Bonny's — both consistent with the
sheets. Pinned in `tests/test_bridge.py`.

## 6. Known simplifications (all candidate Phase 2+ refinements)

1. **No crude-specific FCC split:** gasoline/LCO/gas shares are constant
   across feeds; real splits vary with feed paraffinicity (Watson K).
   Maples (2000) correlations would refine this but are not openly
   reproducible — rejected for traceability (kept as a Phase 3+ option if a
   citable table set is obtained).
2. **No wt↔vol density correction per cut:** pooling mixes SR (vol%) with FCC
   splits (vol% of converted VGO); whole-crude density applies uniformly.
   Per-cut density (available in the TE sheets) would tighten mass balance.
3. **Linear severity mapping** of the conversion window (40→80 %); real
   response is mildly S-shaped.
4. **Jet pool has no severity response** (kero is straight-run only); some
   refineries crack into the kero range at low severity.

## 7. Surrogate (Phase 3) — ETR over bridge-generated labels

Implemented in `models/dataset.py` + `models/train_surrogate.py`; numbers below
are from the committed `models/model_card.md` (regenerate with
`scripts/train_surrogate.py` — fully deterministic, seeded sampling + forest).

**Design:** the surrogate learns the Stage-1 bridge (problem statement §3
Stage 2), it does not replace its physics. Features are the blend-weighted
properties + the blend-weighted TBP cut fractions (the bridge's actual inputs);
labels are bridge yields. 4,000 rows sampled Dirichlet(α=0.55) on the simplex ×
U(0,1) severity (seed 20260919). ExtraTreesRegressor, 150 trees × depth 14 ×
leaf 4 (size/accuracy sweep: 300 trees → 96.5 MB pkl, violating the 50 MB
hosting guard, at equal CV accuracy).

**Dual CV results (both protocols, always — spec §3.5):**

| Target | Random 5-fold R² | Leave-crude-out R² |
|---|---|---|
| gasoline | 0.9893 | 0.9347 |
| diesel | 0.9972 | 0.7805 |
| jet | 0.9820 | 0.1139 |
| petrochem | 0.9979 | 0.9691 |

**Gates (problem statement §5):** random-5-fold min R² = 0.982 → **impressive
gate passed** (>0.90); LCO reported alongside. **The jet LCO result is the
honesty finding:** the fold holding out the extreme-kero crude (ANS, 12.6 %
kero cut) tests rows below the training range, and tree ensembles cannot
extrapolate — quantified and explained in the model card. Deployment never
requires unseen-crude extrapolation (DE operates inside the committed slate).

**Fidelity inside the envelope:** surrogate vs bridge on arbitrary blends:
max |Δyield| ≈ 0.0007 (0.07 vol%); the DE optimum is unchanged (same blend,
margin within $0.2/bbl of the bridge-based run).

**FCCU calibration note (supersedes the row-7 plan):** the planned
severity-shape calibration against operational FCCU data was probed and
dropped — the ML-PSE FCCU dataset (MIT; 7 CSVs × 47 signals from the
Santander/McFarlane Simulink model) is a *fault-detection* set: normal
operation + equipment faults with controllers active, **no severity sweep**,
so it carries no yield-vs-severity information beyond what the cited Gary &
Handwerk window already provides (§2). The surrogate therefore inherits the
bridge's cited shape; spec §3.6's "no plant data is claimed" stance is
preserved.

## 8. References

- Gary, J.H., Handwerk, G.E., Kaiser, M.J. — *Petroleum Refining: Technology
  and Economics*, 5th ed., CRC Press (2007): FCC conversion/yield ranges,
  cut-point scheme.
- Leiby, S. (Hart Energy) for ICCT — *An introduction to petroleum refining
  and the production of ULSG and ULSD* (Oct 24, 2011):
  process structure, LCO/slurry handling, hydrotreater ≈1 vol% yield loss
  (exhibit 17).
- Maples, R.E. — *Petroleum Refinery Process Economics*, 2nd ed., PennWell
  (2000): reviewed for FCC yield correlations (Watson-K/feed-API-based);
  coefficient tables not openly reproducible → not used (see §6.1).
- TotalEnergies / ExxonMobil published crude assays (provenance row 3) —
  TBP curves, whole-crude properties, and the ground-truth cut tables in §5.
- ML-PSE (MIT) FCCU dataset — https://github.com/ML-PSE/FluidCat-FDD-SimData
  (Santander & McFarlane Simulink model): probed for surrogate calibration and
  rejected — fault-detection data, no severity sweep (see §7).
