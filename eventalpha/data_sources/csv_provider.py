"""CSV-backed market data provider."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import yaml

from eventalpha.config import get_rules_dir
from eventalpha.schemas import MarketDataError, PricePoint, PriceSeries

from .base import MarketDataProvider
from .returns import calculate_return_from_prices


class CSVMarketDataProvider(MarketDataProvider):
    """Read local demo prices and calculate returns from close series."""

    def __init__(
        self,
        csv_path: str | Path,
        asset_mapping_path: str | Path | None = None,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.asset_mapping_path = (
            Path(asset_mapping_path)
            if asset_mapping_path
            else get_rules_dir() / "asset_code_mapping.yaml"
        )
        self.asset_mapping = self._load_asset_mapping()
        self._series_by_asset = self._load_csv()

    def get_price_series(
        self,
        asset_name: str,
        start_date: str,
        end_date: str,
    ) -> PriceSeries:
        """Return close prices for an asset between two dates."""
        provider_symbol = self._resolve_provider_symbol(asset_name)
        if provider_symbol not in self._series_by_asset:
            raise MarketDataError(f"Missing market data for asset: {asset_name}")

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        points = [
            point
            for point in self._series_by_asset[provider_symbol].points
            if start <= point.date <= end
        ]
        if not points:
            raise MarketDataError(
                f"No price data for {asset_name} between {start_date} and {end_date}"
            )
        return PriceSeries(asset_name=asset_name, points=points)

    def get_asset_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Calculate asset return from CSV close prices."""
        return self._get_return(asset_name, horizon, start_date)

    def get_benchmark_return(
        self,
        benchmark: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Calculate benchmark return from CSV close prices."""
        return self._get_return(benchmark, horizon, start_date)

    def _get_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None,
    ) -> float:
        if start_date is None:
            raise MarketDataError(
                f"CSVMarketDataProvider requires start_date for {asset_name}"
            )
        provider_symbol = self._resolve_provider_symbol(asset_name)
        if provider_symbol not in self._series_by_asset:
            raise MarketDataError(f"Missing market data for asset: {asset_name}")
        return calculate_return_from_prices(
            self._series_by_asset[provider_symbol],
            start_date,
            horizon,
        )

    def _load_asset_mapping(self) -> dict:
        if not self.asset_mapping_path.exists():
            return {}
        return yaml.safe_load(self.asset_mapping_path.read_text(encoding="utf-8")) or {}

    def _resolve_provider_symbol(self, asset_name: str) -> str:
        config = self.asset_mapping.get(asset_name, {})
        if config.get("provider", "csv") != "csv":
            return asset_name
        return config.get("provider_symbol", asset_name)

    def _load_csv(self) -> dict[str, PriceSeries]:
        if not self.csv_path.exists():
            raise MarketDataError(f"CSV market data file not found: {self.csv_path}")

        grouped: dict[str, list[PricePoint]] = {}
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"date", "asset_name", "close"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise MarketDataError(
                    "CSV must contain columns: date, asset_name, close"
                )
            for line_number, row in enumerate(reader, start=2):
                asset_name = (row.get("asset_name") or "").strip()
                if not asset_name:
                    raise MarketDataError(f"Missing asset_name at line {line_number}")
                try:
                    point_date = date.fromisoformat((row.get("date") or "").strip())
                    close = float((row.get("close") or "").strip())
                except ValueError as exc:
                    raise MarketDataError(
                        f"Invalid date or close at line {line_number}"
                    ) from exc
                grouped.setdefault(asset_name, []).append(
                    PricePoint(date=point_date, close=close)
                )

        series_by_asset = {}
        for asset_name, points in grouped.items():
            ordered = sorted(points, key=lambda point: point.date)
            series_by_asset[asset_name] = PriceSeries(asset_name=asset_name, points=ordered)
        return series_by_asset
