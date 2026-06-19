"""Return calculation helpers for price-series based providers."""

from __future__ import annotations

from datetime import date

from eventalpha.schemas import MarketDataError, MarketReturn, PriceSeries


HORIZON_TO_TRADING_DAYS = {
    "T+1": 1,
    "T+3": 3,
    "T+7": 7,
}


def calculate_return_from_prices(
    price_series: PriceSeries,
    start_date: str,
    horizon: str,
) -> float:
    """Calculate T+N return using available trading days after start_date."""
    return calculate_market_return(price_series, start_date, horizon).return_value


def calculate_market_return(
    price_series: PriceSeries,
    start_date: str,
    horizon: str,
) -> MarketReturn:
    """Calculate detailed T+N return from sorted close prices."""
    if horizon not in HORIZON_TO_TRADING_DAYS:
        raise MarketDataError(f"Unsupported horizon: {horizon}")
    if not price_series.points:
        raise MarketDataError(f"No price points for asset: {price_series.asset_name}")

    parsed_start = date.fromisoformat(start_date)
    candidates = [point for point in price_series.points if point.date >= parsed_start]
    if not candidates:
        raise MarketDataError(
            f"No price data for {price_series.asset_name} on or after {start_date}"
        )

    target_index = HORIZON_TO_TRADING_DAYS[horizon]
    if len(candidates) <= target_index:
        raise MarketDataError(
            f"Insufficient price data for {price_series.asset_name}: "
            f"need {horizon} after {start_date}, have {len(candidates) - 1} trading days"
        )

    start_point = candidates[0]
    end_point = candidates[target_index]
    if start_point.close == 0:
        raise MarketDataError(f"Start close is zero for {price_series.asset_name}")

    return_value = round(end_point.close / start_point.close - 1.0, 6)
    return MarketReturn(
        asset_name=price_series.asset_name,
        horizon=horizon,  # type: ignore[arg-type]
        start_date=start_point.date,
        end_date=end_point.date,
        start_close=start_point.close,
        end_close=end_point.close,
        return_value=return_value,
    )
