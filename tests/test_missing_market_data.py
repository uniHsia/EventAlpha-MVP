"""Missing and insufficient market data tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventalpha.data_sources import CSVMarketDataProvider, calculate_return_from_prices
from eventalpha.schemas import MarketDataError, PricePoint, PriceSeries


def test_missing_asset_raises_clear_error() -> None:
    """CSVProvider should raise MarketDataError for unknown assets."""
    csv_path = Path(__file__).parent / "fixtures" / "market_prices_demo.csv"
    provider = CSVMarketDataProvider(csv_path)

    with pytest.raises(MarketDataError, match="Missing market data"):
        provider.get_asset_return("不存在的资产", "T+3", start_date="2026-06-18")


def test_insufficient_horizon_data_raises_clear_error() -> None:
    """Return calculation should fail when T+N data is not available."""
    series = PriceSeries(
        asset_name="短序列",
        points=[
            PricePoint(date="2026-06-18", close=100),
            PricePoint(date="2026-06-19", close=101),
        ],
    )

    with pytest.raises(MarketDataError, match="Insufficient price data"):
        calculate_return_from_prices(series, "2026-06-18", "T+7")
