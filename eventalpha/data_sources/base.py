"""Market data provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from eventalpha.schemas import PriceSeries


class MarketDataProvider(ABC):
    """Minimal market data provider contract for review."""

    @abstractmethod
    def get_price_series(
        self,
        asset_name: str,
        start_date: str,
        end_date: str,
    ) -> PriceSeries:
        """Return close prices for an asset between two dates."""

    @abstractmethod
    def get_asset_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Return asset return for a review horizon."""

    @abstractmethod
    def get_benchmark_return(
        self,
        benchmark: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Return benchmark return for a review horizon."""
