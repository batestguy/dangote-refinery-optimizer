"""Convergence + sensitivity plots (Phase 4 deliverable, spec §5).

Matplotlib (declared dep); every figure saved by scripts/sensitivity_study.py
lands in docs/assets/ and is committed — recruiter-visible evidence.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")  # headless-safe (CI, scripts)
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def plot_convergence(
    history: Sequence[float],
    lp_margin: float | None = None,
    equal_weight_margin: float | None = None,
    ax: plt.Axes | None = None,
) -> plt.Figure:
    """DE best-value-per-iteration curve with reference lines.

    Args:
        history: best objective (negative margin) per iteration from
            ``BlendOptimizationResult.convergence``.
        lp_margin: optional LP baseline margin (the honest bar).
        equal_weight_margin: optional equal-weight baseline margin.

    Returns:
        The matplotlib figure (caller saves or shows).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4))
    iters = np.arange(1, len(history) + 1)
    ax.plot(
        iters, -np.asarray(history, dtype=float), lw=1.8, color="#1f77b4", label="DE best margin"
    )
    ax.set_xlabel("DE iteration")
    ax.set_ylabel("Margin ($/bbl)")
    if equal_weight_margin is not None:
        ax.axhline(equal_weight_margin, color="#7f7f7f", ls="--", lw=1.2, label="equal-weight")
    if lp_margin is not None:
        ax.axhline(lp_margin, color="#d62728", ls=":", lw=1.4, label="LP optimum (honest bar)")
    ax.set_title("Differential evolution convergence (spec §5 Phase 4)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    fig = ax.figure
    fig.tight_layout()
    return fig


def plot_seed_sensitivity(
    margins: Sequence[float],
    ax: plt.Axes | None = None,
) -> plt.Figure:
    """Histogram of final margins across the ≥100-seed sensitivity sweep.

    Args:
        margins: best unpenalized margin per seed.

    Returns:
        The matplotlib figure (caller saves or shows).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4))
    m = np.asarray(margins, dtype=float)
    ax.hist(m, bins=20, color="#1f77b4", alpha=0.85, edgecolor="white")
    ax.axvline(m.mean(), color="#d62728", lw=1.6, label=f"mean ${m.mean():.2f}")
    ax.axvline(np.median(m), color="#ff7f0e", lw=1.4, ls="--", label=f"median ${np.median(m):.2f}")
    ax.set_xlabel("Best margin ($/bbl)")
    ax.set_ylabel("Seeds")
    ax.set_title(f"Seed sensitivity, n={len(m)} runs (spec §3.4: ≥100 seeds)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, axis="y")
    fig = ax.figure
    fig.tight_layout()
    return fig
