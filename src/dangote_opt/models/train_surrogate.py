"""Phase 3: Extremely Randomized Trees surrogate.

Contract (spec §3.5, locked decision 10):
- Train on Stage-1 bridge labels (blend-weighted properties + severity → 4 yields).
- Dual CV protocol, BOTH reported side-by-side in the model card:
    * random 5-fold (headline, comparable to published numbers)
    * GroupKFold leave-crude-out (honesty metric; the gap IS a finding)
- SHAP analysis + models/model_card.md are Phase 3 deliverables.
- RAM guard: ≤500 trees, depth-limited, .pkl <50 MB (app hosting, spec §3.7).
"""

from __future__ import annotations

import pandas as pd


def train_etr_surrogate(features: pd.DataFrame, labels: pd.DataFrame) -> dict:
    """Train ETR, run the dual-CV protocol, persist model + model card data.

    Args:
        features: blend-weighted crude properties + severity per row.
        labels: 4-product yield columns matching CONFIG.products.

    Returns:
        Dict with keys: model, cv_random, cv_leave_crude_out, shap_summary, card.

    Raises:
        NotImplementedError: Phase 3 (needs Phase 2 bridge labels first).
    """
    raise NotImplementedError("Phase 3: ETR + dual-CV protocol (spec §3.5)")
