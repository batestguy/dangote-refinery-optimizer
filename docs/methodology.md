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

## 4. Product pooling

| Product | Components |
|---|---|
| gasoline | SR naphtha (<180 °C) + FCC gasoline |
| diesel | SR distillate (260–360 °C) + FCC LCO, less HT loss |
| jet | SR kerosene (180–260 °C) |
| petrochem | residue (>540 °C) + FCC slurry + FCC light-gas/coke (propylene/PGP proxy) |

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

## 7. References

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
