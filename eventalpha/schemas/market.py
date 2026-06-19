"""Market data schemas and errors."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from .base import Horizon, EventAlphaModel


class MarketDataError(Exception):
    """Raised when market data is missing, invalid, or insufficient."""


class PricePoint(EventAlphaModel):
    """One close price observation."""

    date: date
    close: float


class PriceSeries(EventAlphaModel):
    """Close price series for one asset."""

    asset_name: str
    points: list[PricePoint] = Field(default_factory=list)


class MarketReturn(EventAlphaModel):
    """Calculated return for one asset and review horizon."""

    asset_name: str
    horizon: Horizon
    start_date: date
    end_date: date
    start_close: float
    end_close: float
    return_value: float
