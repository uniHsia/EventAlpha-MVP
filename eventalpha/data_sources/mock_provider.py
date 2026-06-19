"""Deterministic mock market data provider."""

from __future__ import annotations

from datetime import date, timedelta

from eventalpha.schemas import PricePoint, PriceSeries

from .base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    """Return fixed returns for demo assets and benchmarks."""

    def __init__(self) -> None:
        self.asset_returns: dict[tuple[str, str], float] = {
            ("国产 AI 芯片", "T+1"): 0.030,
            ("国产 AI 芯片", "T+3"): 0.080,
            ("国产 AI 芯片", "T+7"): 0.060,
            ("服务器", "T+1"): 0.020,
            ("服务器", "T+3"): 0.050,
            ("服务器", "T+7"): 0.035,
            ("先进封装", "T+1"): 0.008,
            ("先进封装", "T+3"): 0.020,
            ("先进封装", "T+7"): 0.018,
            ("国产 EDA", "T+3"): 0.018,
            ("半导体设备", "T+3"): -0.010,
            ("半导体设备", "T+7"): -0.015,
            ("原油", "T+3"): 0.024,
            ("原油", "T+7"): 0.010,
            ("黄金", "T+3"): 0.021,
            ("黄金", "T+7"): 0.012,
            ("供应链替代主题", "T+1"): -0.006,
            ("供应链替代主题", "T+3"): -0.020,
            ("供应链替代主题", "T+7"): -0.012,
            ("成长风格指数", "T+1"): 0.001,
            ("成长风格指数", "T+3"): 0.002,
            ("成长风格指数", "T+7"): 0.004,
        }
        self.benchmark_returns: dict[tuple[str, str], float] = {
            ("沪深300", "T+1"): 0.002,
            ("沪深300", "T+3"): 0.008,
            ("沪深300", "T+7"): 0.006,
            ("美元指数", "T+3"): 0.003,
            ("全球权益基准", "T+3"): -0.004,
        }

    def get_price_series(
        self,
        asset_name: str,
        start_date: str,
        end_date: str,
    ) -> PriceSeries:
        """Return a synthetic flat price series for interface compatibility."""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        days = max((end - start).days, 0)
        points = [
            PricePoint(date=start + timedelta(days=offset), close=100.0)
            for offset in range(days + 1)
        ]
        return PriceSeries(asset_name=asset_name, points=points)

    def get_asset_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Return a fixed mock return for the asset."""
        return self.asset_returns.get((asset_name, horizon), 0.0)

    def get_benchmark_return(
        self,
        benchmark: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Return a fixed mock return for the benchmark."""
        return self.benchmark_returns.get((benchmark, horizon), 0.0)
