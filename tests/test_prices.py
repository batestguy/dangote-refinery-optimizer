"""Product-price anchor tests — window math, unit transform, petrochem
placeholder disclosure, and the committed artifact's integrity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dangote_opt.config import CONFIG
from dangote_opt.data.prices import (
    GAL_PER_BBL,
    PRODUCT_SERIES,
    prices_vector,
    product_prices,
)

PRICES_PARQUET = Path("data/derived/prices_phase2.parquet")


def make_frame(products: dict[str, list[tuple[str, float]]]) -> pd.DataFrame:
    rows = [
        {"period": period, "product": code, "value": val, "units": "$/gal"}
        for code, series in products.items()
        for period, val in series
    ]
    return pd.DataFrame(rows)


def test_product_prices_trailing_window_and_unit_transform():
    # 24 months of rising prices; only the last 12 must be averaged.
    periods = [f"{y}-{m:02d}" for y in (2024, 2025) for m in range(1, 13)]
    vals = np.linspace(1.5, 2.5, 24)  # $/gal
    frame = make_frame(
        {code: list(zip(periods, vals, strict=True)) for code in PRODUCT_SERIES.values()}
    )
    prices = product_prices(frame, end_period="2025-12", months=12)
    expected_bbl = float(vals[-12:].mean()) * GAL_PER_BBL
    assert prices["gasoline"] == pytest.approx(round(expected_bbl, 2))


def test_product_prices_insufficient_history_raises():
    frame = make_frame({"EPJK": [(f"2025-{m:02d}", 2.0) for m in range(1, 7)]})
    with pytest.raises(ValueError, match="need 12"):
        product_prices(frame, end_period="2025-06", months=12)


def test_petrochem_is_disclosed_placeholder():
    periods = [f"2025-{m:02d}" for m in range(1, 13)]
    frame = make_frame(
        {
            "EPMRU": list(zip(periods, [2.0] * 12, strict=True)),
            "EPD2DXL0": list(zip(periods, [2.2] * 12, strict=True)),
            "EPJK": list(zip(periods, [2.1] * 12, strict=True)),
        }
    )
    prices = product_prices(frame, end_period="2025-12", months=12)
    assert set(prices) == set(CONFIG.products)
    assert prices["petrochem"] == CONFIG.default_prices["petrochem"]
    assert prices["gasoline"] == pytest.approx(2.0 * GAL_PER_BBL)


def test_prices_vector_matches_config_order():
    periods = [f"2025-{m:02d}" for m in range(1, 13)]
    frame = make_frame(
        {code: list(zip(periods, [1.0] * 12, strict=True)) for code in PRODUCT_SERIES.values()}
    )
    vec = prices_vector(frame, end_period="2025-12", months=12)
    assert len(vec) == len(CONFIG.products)
    # gasoline/diesel/jet all 42.0 ($1/gal × 42); petrochem placeholder
    assert vec[0] == pytest.approx(42.0)
    assert vec[1] == pytest.approx(42.0)
    assert vec[2] == pytest.approx(42.0)
    assert vec[3] == CONFIG.default_prices["petrochem"]


def test_committed_prices_artifact_is_valid():
    assert PRICES_PARQUET.exists(), "run scripts/build_prices.py and commit the output"
    df = pd.read_parquet(PRICES_PARQUET)
    assert set(df["product"]) == set(CONFIG.products)
    sidecar = json.loads((PRICES_PARQUET.parent / "prices_phase2.json").read_text())
    for _, row in df.iterrows():
        assert row["price_usd_bbl"] == pytest.approx(sidecar["prices_usd_bbl"][row["product"]])
        if row["product"] == "petrochem":
            assert "PLACEHOLDER" in row["status"]
        else:
            assert "REAL" in row["status"]
