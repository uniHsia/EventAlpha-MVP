"""Market data provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    """Minimal market data provider contract for review."""

    @abstractmethod
    def get_asset_return(self, asset_name: str, horizon: str) -> float:
        """Return asset return for a review horizon."""

    @abstractmethod
    def get_benchmark_return(self, benchmark: str, horizon: str) -> float:
        """Return benchmark return for a review horizon."""
