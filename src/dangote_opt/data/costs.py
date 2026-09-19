"""Crude-cost anchor — EIA Brent (real) + documented per-grade differentials.

Provenance row 9 contract: EIA carries no Bonny Light/Forcados/… spot series,
so delivered crude cost is modeled as

    cost_j = Brent_reference + differential_j          [USD/bbl]

where ``Brent_reference`` is the trailing-12-month average of the real EIA
Brent spot series (cache-first via acquire.CATALOG["brent_spot"]) and every
differential is an **ASSUMED, quality-based** value documented in the
``DIFFERENTIALS`` table below — never presented as observed market data.
Refresh path: OPEC Monthly Oil Market Reports (MOMR) publish actual Bonny
Light / Forcados / Qua Iboe monthly averages; replace ASSUMED values there
when pulled (Phase 2+ task).

Ordering sanity (verified in tests): differentials decrease with API within a
sulfur class and turn negative once sulfur is high enough to offset gravity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from dangote_opt.data.acquire import CATALOG, fetch_eia_series

BRENT_SERIES_KEY = "brent_spot"
DEFAULT_COST_WINDOW_MONTHS = 12


@dataclass(frozen=True)
class Differential:
    """One grade's assumed differential to Brent (USD/bbl)."""

    crude_id: str
    name: str
    diff_usd_bbl: float
    basis: str  # quality rationale; must state API/sulfur
    status: str = "ASSUMED"  # ASSUMED | OPEC_MOMR (once refreshed)


# Delivered-cost differentials to Brent — ASSUMED, quality-based (see module
# docstring). Nigerian lights price at/above Brent on light-sweet quality but
# below it on freight to typical export markets; net small premia. Sour grades
# discount, heavier sweet grades discount mildly.
DIFFERENTIALS: tuple[Differential, ...] = (
    Differential(
        "bonny_light",
        "Bonny Light",
        +1.0,
        "light sweet (API 34.9, S 0.15%): quality premium, freight-discounted",
    ),
    Differential(
        "forcados",
        "Forcados",
        +0.5,
        "light sweet, slightly heavier (API 31.5, S 0.22%): smaller premium",
    ),
    Differential(
        "qua_iboe",
        "Qua Iboe",
        +1.5,
        "lightest sweet Nigerian (API 37.3, S 0.12%): largest quality premium",
    ),
    Differential(
        "alaska_north_slope",
        "Alaska North Slope",
        -2.5,
        "medium sour (API 32.3, S 1.04%): sulfur discount dominates",
    ),
    Differential(
        "thunder_horse",
        "Thunder Horse",
        -1.0,
        "medium, moderate sulfur (API 34.5, S 0.76%): mild sour discount",
    ),
)


def load_brent_reference(
    cache_dir: Path = Path("data/raw/eia"),
    *,
    end_period: str | None = None,
    months: int = DEFAULT_COST_WINDOW_MONTHS,
    api_key: str | None = None,
) -> tuple[float, pd.DataFrame]:
    """Trailing-``months`` average of the real EIA Brent spot series.

    Args:
        cache_dir: parquet cache location (data/raw/ is gitignored).
        end_period: last 'YYYY-MM' to include (default: latest cached/pulled).
        months: trailing window length (12 = annual anchor).
        api_key: EIA key; when None, only the cache is consulted (offline-safe).

    Returns:
        (brent_reference_usd_bbl, brent_frame) — the frame covers the window.

    Raises:
        ValueError: fewer than ``months`` rows available in the window.
    """
    series = CATALOG[BRENT_SERIES_KEY]
    if api_key:
        # Wide pull; the cache makes repeat calls free.
        df = fetch_eia_series(series, api_key, start="2015-01", end="2025-12", cache_dir=cache_dir)
    else:
        from dangote_opt.data.acquire import _cache_key, _facet_params

        query = {
            "frequency": series.frequency,
            "data[]": list(series.data_columns),
            **_facet_params(series.facets),
        }
        cache_path = cache_dir / f"{_cache_key(series.route, query)}.parquet"
        if not cache_path.exists():
            raise FileNotFoundError(
                f"{cache_path} missing and no API key given — pull Brent first "
                "(run with api_key) or offline use is impossible"
            )
        df = pd.read_parquet(cache_path)

    df = df.sort_values("period")
    if end_period is not None:
        df = df[df["period"] <= end_period]
    window = df.tail(months)
    if len(window) < months:
        raise ValueError(f"need {months} Brent months, found {len(window)} — widen the pull window")
    return float(window["value"].mean()), window


def build_crude_costs(
    crude_ids: list[str],
    brent_reference: float,
    differentials: tuple[Differential, ...] = DIFFERENTIALS,
) -> dict[str, float]:
    """Map each slate crude to its delivered cost: Brent + differential.

    Raises:
        KeyError: a slate crude has no documented differential — the cost model
            must never silently default.
    """
    table = {d.crude_id: d for d in differentials}
    missing = [cid for cid in crude_ids if cid not in table]
    if missing:
        raise KeyError(f"no documented differential for: {missing} — add to DIFFERENTIALS")
    return {cid: round(brent_reference + table[cid].diff_usd_bbl, 2) for cid in crude_ids}


def costs_frame(
    brent_reference: float,
    differentials: tuple[Differential, ...] = DIFFERENTIALS,
) -> pd.DataFrame:
    """Documentation-ready frame: per-grade differential, basis, final cost."""
    return pd.DataFrame(
        [
            {
                "crude_id": d.crude_id,
                "name": d.name,
                "differential_usd_bbl": d.diff_usd_bbl,
                "status": d.status,
                "basis": d.basis,
                "cost_usd_bbl": round(brent_reference + d.diff_usd_bbl, 2),
            }
            for d in differentials
        ]
    )
