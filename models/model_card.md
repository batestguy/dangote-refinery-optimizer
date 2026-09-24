# Model Card — ETR Yield Surrogate (Phase 3)

**Trained:** 2026-09-19 · **Labels:** Stage-1 TBP bridge (docs/methodology.md) — synthetic, cited; no measured labels (spec §3.6)

## Training data
- 4000 rows; sampling: Dirichlet(α=0.55) × U(0,1) severity, seed 20260919
- Slate: Bonny Light, Forcados, Qua Iboe, Alaska North Slope, Thunder Horse (provenance row 3)

## Hyperparameters
n_estimators=150, max_depth=14, min_samples_leaf=4, max_features=1.0, seed=20260919

## Dual cross-validation (both protocols, always — spec §3.5)
### Random 5-fold (headline)
| Target | R² | MAE |
|---|---|---|
| yield_gasoline | 0.9893 | 0.00160 |
| yield_diesel | 0.9972 | 0.00092 |
| yield_jet | 0.9820 | 0.00089 |
| yield_petrochem | 0.9979 | 0.00121 |

### Leave-crude-out GroupKFold (honesty metric)
| Target | R² | MAE |
|---|---|---|
| yield_gasoline | 0.9347 | 0.00363 |
| yield_diesel | 0.7805 | 0.00475 |
| yield_jet | 0.1139 | 0.00245 |
| yield_petrochem | 0.9691 | 0.00349 |

**Honesty analysis (jet R² low — explained):** the LCO fold holding out the crude with the extreme kerosene cut (Alaska North Slope, 12.6 % kero vs 14–17 % for the rest) tests rows *below* the training range of the jet label. Tree ensembles predict leaf means and cannot extrapolate, so that fold scores ≈ 0 while the other four interpolate well. Quantified finding, not a defect: DE always operates *inside* the committed 5-crude slate (all crudes available), so deployment never requires unseen-crude extrapolation — the LCO number bounds what would happen if a slate position were swapped for a qualitatively new crude.

## Permutation importance (ΔR², 10 repeats)
- **yield_gasoline:** severity (1.671), cut_diesel (0.136), cut_residue (0.036)
- **yield_diesel:** cut_diesel (0.531), cut_residue (0.116), severity (0.085)
- **yield_jet:** sulfur_blend (0.248), cut_residue (0.239), cut_diesel (0.086)
- **yield_petrochem:** severity (0.793), cut_residue (0.149), cut_diesel (0.128)

## Guards
- inputs clipped into the training envelope at prediction time; pkl held under 50 MB (150 trees × depth 14; 500/16 caps)
- Severity training range: [0.0001534620960719213, 0.999809697240765] — inputs clipped into it

## Gates (problem statement §5)
- Viable: random-5-fold R² > 0.8 — PASS
- Impressive: > 0.9 — PASS
- LCO reported alongside: yes

## Interpretability choice
Permutation importance (ΔR²) over SHAP: same reproducible definition for tree ensembles without an extra dependency; SHAP reviewed and rejected for traceability (docs/methodology.md §6.1 pattern).