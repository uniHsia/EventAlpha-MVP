"""Price-series return calculation tests."""

from __future__ import annotations

import pytest

from eventalpha.data_sources import calculate_return_from_prices
from eventalpha.schemas import PricePoint, PriceSeries


def _series() -> PriceSeries:
    return PriceSeries(
        asset_name="测试资产",
        points=[
            PricePoint(date="2026-06-18", close=100),
            PricePoint(date="2026-06-19", close=101),
            PricePoint(date="2026-06-22", close=102),
            PricePoint(date="2026-06-23", close=103),
            PricePoint(date="2026-06-24", close=104),
            PricePoint(date="2026-06-25", close=105),
            PricePoint(date="2026-06-26", close=106),
            PricePoint(date="2026-06-29", close=107),
        ],
    )


def test_t_plus_returns_use_available_trading_days() -> None:
    """T+N should use the Nth available date after the start price."""
    series = _series()

    assert calculate_return_from_prices(series, "2026-06-18", "T+1") == pytest.approx(0.01)
    assert calculate_return_from_prices(series, "2026-06-18", "T+3") == pytest.approx(0.03)
    assert calculate_return_from_prices(series, "2026-06-18", "T+7") == pytest.approx(0.07)


def test_non_trading_start_uses_next_available_day() -> None:
    """A non-trading start date should roll forward to the next available price."""
    series = _series()

    assert calculate_return_from_prices(series, "2026-06-20", "T+3") == pytest.approx(
        round(105 / 102 - 1, 6)
    )
