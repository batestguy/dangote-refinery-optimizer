"""Phase 1: data acquisition functions.

Sources and their contracts (docs/data_provenance.md is the verified source table):
- EIA Open Data v2 (free API key in .env): product prices, refinery utilization.
  Cache every pull to data/raw/ as parquet — never re-hit the API for the same window.
- Public crude assays (ExxonMobil, TotalEnergies, Equinor, NUPRC): parsed into
  (api, sulfur_pct, tbp_curve) records for the 5-crude slate.
- CrudeOilMix (HF, streaming only — minimal-first decision, spec §4 row 6):
  stream + filter columns/strata; never bulk-download.
- Electric Sheep Africa: Dangote metadata only (capacity, utilization); labeled
  synthetic wherever displayed.

Implemented in Phase 1.
"""

from __future__ import annotations

import pandas as pd


def fetch_eia_series(series_id: str, api_key: str, start: str, end: str) -> pd.DataFrame:
    """Fetch an EIA v2 series window and return a tidy DataFrame.

    Args:
        series_id: EIA series route (e.g. 'PET.EPD2DXL0_NUS_DPG.M').
        api_key: from EIA_API_KEY env var (see .env.example).
        start: ISO date 'YYYY-MM-DD'.
        end: ISO date 'YYYY-MM-DD'.

    Returns:
        DataFrame with columns [date, value, series_id], cached to data/raw/.

    Raises:
        NotImplementedError: Phase 1.
    """
    raise NotImplementedError(
        "Phase 1: EIA v2 client with parquet caching (docs/data_provenance.md)"
    )
