# Problem Statement

**Status:** v1.0 — Phase 0 deliverable (spec §5). Governs all modeling work.

## 1. Decision problem

Choose the crude diet (blend ratios `x_j`) and FCC severity (`s`) that maximize refinery margin per blended barrel, subject to physical and quality constraints.

## 2. Formulation

**Objective** (brief §3.2, amended by spec §3.4/§3.6):

```
maximize   M(x, s) = Σᵢ yieldᵢ(x, s) · priceᵢ  −  Σⱼ xⱼ · costⱼ
```

**Decision variables**
- `x_j ≥ 0`, `Σ x_j = 1` — blend ratios over a 5-crude slate
- `s ∈ [0, 1]` — normalized FCC conversion proxy (unit-level temperatures/catalyst ratios are *despecified* — spec §3.6; no plant data is claimed)

**Constraints**
| Constraint | Form | Source |
|---|---|---|
| Blend API window | `30 ≤ Σ x_j·API_j ≤ 45` | brief §3.2 (linear blending) |
| Blend sulfur cap | `Σ x_j·S_j ≤ 1.5 wt-%` | brief §3.2 |
| Gasoline RON | linear blend index ≥ 91 | spec §3.3 (Phase 2) |
| Diesel sulfur | blend ≤ 50 ppm | spec §3.3 (Phase 2) |
| Diesel cetane index | LBI ≥ 45 | spec §3.3 (Phase 2) |
| Jet freeze point | proxy ≤ −47 °C | spec §3.3 (Phase 2) |
| Gasoline RVP | LBI ≤ 60 kPa | spec §3.3 (Phase 2) |
| Severity bounds | `0 ≤ s ≤ 1` | config |

Constraint handling in DE (implemented in `src/dangote_opt/optimization/objective.py`): **simplex repair** for `Σx=1`; **quadratic penalty** (`CONFIG.constraint_penalty`) for the API window and sulfur cap, so an infeasible blend can never out-score a feasible one; severity clipped. The quality-spec LBIs join the same penalty block in Phase 2/4. Reported margins are always the *unpenalized* value with feasibility shown separately.

## 3. Yield model

`yieldᵢ(x, s)` is produced by a two-stage bridge (spec §3.1):
1. **Stage 1 (Phase 2 — implemented):** TBP cut-point mass balance + cited FCC conversion/product-split ranges → per-crude yield vectors; every constant documented in `docs/methodology.md` and validated against published Bonny Light cut yields (±0.2 vol%).
2. **Stage 2 (Phase 3 — implemented):** ETR surrogate learns the Stage-1 bridge over (blend-weighted properties + blend-weighted TBP cuts, severity); trained on bridge-generated labels. Validated with **dual CV**: random 5-fold (headline, min R² = 0.982) **and** leave-crude-out GroupKFold (honesty metric — jet-crude fold quantifies the extrapolation limit, see `models/model_card.md`) — both reported, never one alone. The planned FCCU-severity-shape calibration was dropped: the MIT ML-PSE FCCU dataset is fault-detection data with no severity sweep (provenance row 7).

## 4. Baseline contract (locked, spec §3.4)

The optimizer's margin is **always** reported alongside, on identical prices/constraints:
1. **Equal-weight** blend at *default* severity (the planner's no-optimization case; spec §3.4),
2. **Random search** (10k feasible draws),
3. **LP optimum** on the linearized model.

If DE ≤ LP, that is reported honestly and analyzed (nonlinearity may be small at 5 crudes — itself a finding).

## 5. Success criteria (brief §1.4, amended by spec §3.5)

| Metric | Viable | Impressive |
|---|---|---|
| Surrogate R² (random 5-fold) | > 0.80 | > 0.90 |
| Surrogate R² (leave-crude-out) | reported | gap quantified & explained |
| Margin uplift vs equal-weight | > 5% | > 10% |
| Vs LP (the honest bar) | reported | positive & mechanistically explained |

## 6. Explicit non-goals

No proprietary Dangote data or claims about its operations · no real-time trading · no Aspen-class simulation · no unit-level "optimal temperatures" presented as findings · single-period, 4-product scope.
