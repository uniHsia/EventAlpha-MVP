"""CSV market data provider loading tests."""

from __future__ import annotations

from pathlib import Path

from eventalpha.data_sources import CSVMarketDataProvider


def test_csv_provider_loads_price_series() -> None:
    """CSVProvider should load sorted float close prices by asset name."""
    csv_path = Path(__file__).parent / "fixtures" / "market_prices_demo.csv"
    provider = CSVMarketDataProvider(csv_path)

    series = provider.get_price_series("国产 AI 芯片", "2026-06-18", "2026-07-01")

    assert series.asset_name == "国产 AI 芯片"
    assert len(series.points) == 10
    assert series.points[0].date.isoformat() == "2026-06-18"
    assert series.points[0].close == 100.0
    assert series.points == sorted(series.points, key=lambda point: point.date)
