"""AkShare-backed market data provider."""

from __future__ import annotations

import csv
import os
import re
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml

from eventalpha.config import PROJECT_ROOT
from eventalpha.schemas import MarketDataError, PricePoint, PriceSeries

from .base import MarketDataProvider
from .returns import calculate_return_from_prices


class AkShareMarketDataProvider(MarketDataProvider):
    """Fetch market prices from AkShare and expose EventAlpha price series."""

    def __init__(
        self,
        mapping_path: str | Path = "eventalpha/rules/asset_code_mapping.yaml",
        cache_dir: str | Path = "data/cache/market_data/akshare",
        use_cache: bool = True,
        refresh_cache: bool = False,
        trust_env: bool = True,
    ) -> None:
        self.mapping_path = self._resolve_path(mapping_path)
        self.cache_dir = self._resolve_path(cache_dir)
        self.use_cache = use_cache
        self.refresh_cache = refresh_cache
        self.trust_env = trust_env
        self.asset_mapping = self._load_asset_mapping()

    def get_price_series(
        self,
        asset_name: str,
        start_date: str,
        end_date: str,
    ) -> PriceSeries:
        """Return AkShare close prices for one mapped asset."""
        config = self.get_asset_config(asset_name)
        provider_type = config["provider_type"]
        symbol = str(config["provider_symbol"])
        eastmoney_secid = config.get("eastmoney_secid")
        cache_path = self._cache_path(asset_name, provider_type, symbol, start_date, end_date)

        if self.use_cache and not self.refresh_cache and cache_path.exists():
            return self._read_cache(cache_path, asset_name)

        try:
            if eastmoney_secid:
                df = self._fetch_eastmoney_direct_dataframe(
                    str(eastmoney_secid),
                    start_date,
                    end_date,
                    asset_name,
                )
            else:
                df = self._fetch_akshare_dataframe(provider_type, symbol, start_date, end_date)
        except MarketDataError:
            raise
        except Exception as exc:  # pragma: no cover - exercised only with live AkShare issues
            raise MarketDataError(
                f"AkShare request failed for {asset_name} ({provider_type}:{symbol}): {exc}"
            ) from exc

        series = self._normalize_akshare_dataframe(df, asset_name)
        if self.use_cache:
            self._write_cache(cache_path, series)
        return series

    def get_asset_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Calculate asset return from AkShare prices."""
        return self._get_return(asset_name, horizon, start_date)

    def get_benchmark_return(
        self,
        benchmark: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Calculate benchmark return from AkShare prices."""
        return self._get_return(benchmark, horizon, start_date)

    def get_asset_config(self, asset_name: str) -> dict[str, Any]:
        """Return AkShare config for an asset or raise a clear mapping error."""
        if asset_name not in self.asset_mapping:
            raise MarketDataError(f"No asset mapping found for: {asset_name}")
        config = self.asset_mapping[asset_name] or {}
        provider = config.get("provider")
        if provider != "akshare":
            raise MarketDataError(
                f"Asset {asset_name} is configured for provider '{provider}', not akshare"
            )
        provider_type = config.get("provider_type")
        provider_symbol = config.get("provider_symbol")
        if not provider_type or not provider_symbol:
            raise MarketDataError(
                f"AkShare mapping for {asset_name} requires provider_type and provider_symbol"
            )
        return config

    def is_akshare_asset(self, asset_name: str) -> bool:
        """Return whether an asset is configured for AkShare."""
        config = self.asset_mapping.get(asset_name) or {}
        return config.get("provider") == "akshare"

    def _get_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None,
    ) -> float:
        if start_date is None:
            raise MarketDataError(
                f"AkShareMarketDataProvider requires start_date for {asset_name}"
            )
        end_date = self._rough_end_date(start_date, horizon)
        series = self.get_price_series(asset_name, start_date, end_date)
        return calculate_return_from_prices(series, start_date, horizon)

    def _fetch_akshare_dataframe(
        self,
        provider_type: str,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Fetch a raw AkShare DataFrame for a supported provider type."""
        start = self._compact_date(start_date)
        end = self._compact_date(end_date)
        with self._proxy_env_disabled_if_needed():
            try:
                import akshare as ak
            except ImportError as exc:  # pragma: no cover - depends on local environment
                raise RuntimeError("AkShare is not installed. Please run: pip install akshare") from exc

            if provider_type == "index":
                return ak.index_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start,
                    end_date=end,
                )
            if provider_type == "stock":
                return ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust="",
                )
            if provider_type == "fund":
                return ak.fund_etf_hist_em(
                    symbol=symbol,
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust="",
                )
        raise MarketDataError(f"Unsupported AkShare provider_type: {provider_type}")

    def _fetch_eastmoney_direct_dataframe(
        self,
        secid: str,
        start_date: str,
        end_date: str,
        asset_name: str,
    ) -> pd.DataFrame:
        """Fetch EastMoney historical K-line data directly by known secid.

        AkShare's index_zh_a_hist first calls a code mapping endpoint that can
        fail independently. For known assets, secid lets us query the historical
        K-line endpoint directly and still normalize into the same PriceSeries.
        """
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",
            "fqt": "0",
            "beg": self._compact_date(start_date),
            "end": self._compact_date(end_date),
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/",
        }
        try:
            session = requests.Session()
            session.trust_env = self.trust_env
            response = session.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise MarketDataError(
                f"EastMoney direct request failed for {asset_name} (secid:{secid}): {exc}"
            ) from exc

        return self._normalize_eastmoney_kline_payload(payload, asset_name, secid)

    def _normalize_eastmoney_kline_payload(
        self,
        payload: dict[str, Any],
        asset_name: str,
        secid: str,
    ) -> pd.DataFrame:
        """Convert EastMoney kline JSON into the DataFrame shape used by normalizer."""
        data = payload.get("data") if isinstance(payload, dict) else None
        klines = data.get("klines") if isinstance(data, dict) else None
        if not klines:
            raise MarketDataError(
                f"EastMoney direct data for {asset_name} (secid:{secid}) has no klines"
            )

        rows: list[dict[str, Any]] = []
        for item in klines:
            parts = str(item).split(",")
            if len(parts) < 3:
                raise MarketDataError(
                    f"Invalid EastMoney kline row for {asset_name} (secid:{secid})"
                )
            rows.append({"日期": parts[0], "收盘": parts[2]})
        return pd.DataFrame(rows)

    def _normalize_akshare_dataframe(
        self,
        df: pd.DataFrame,
        asset_name: str,
    ) -> PriceSeries:
        """Convert an AkShare DataFrame into a normalized PriceSeries."""
        if df is None or df.empty:
            raise MarketDataError(f"AkShare returned no rows for {asset_name}")

        date_col = self._find_column(df, ["日期", "date"])
        close_col = self._find_column(df, ["收盘", "close"])
        if date_col is None:
            raise MarketDataError(f"AkShare data for {asset_name} is missing 日期/date column")
        if close_col is None:
            raise MarketDataError(f"AkShare data for {asset_name} is missing 收盘/close column")

        points: list[PricePoint] = []
        for _, row in df.iterrows():
            raw_close = row[close_col]
            if pd.isna(raw_close):
                continue
            try:
                point_date = pd.to_datetime(row[date_col]).date()
                close = float(raw_close)
            except (TypeError, ValueError) as exc:
                raise MarketDataError(f"Invalid AkShare row for {asset_name}") from exc
            points.append(PricePoint(date=point_date, close=close))

        if not points:
            raise MarketDataError(f"AkShare data for {asset_name} has no valid close prices")
        points.sort(key=lambda point: point.date)
        return PriceSeries(asset_name=asset_name, points=points)

    def _load_asset_mapping(self) -> dict[str, Any]:
        if not self.mapping_path.exists():
            raise MarketDataError(f"Asset mapping file not found: {self.mapping_path}")
        return yaml.safe_load(self.mapping_path.read_text(encoding="utf-8")) or {}

    def _read_cache(self, cache_path: Path, asset_name: str) -> PriceSeries:
        points: list[PricePoint] = []
        with cache_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"date", "asset_name", "close"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise MarketDataError(f"Invalid AkShare cache file: {cache_path}")
            for row in reader:
                try:
                    points.append(
                        PricePoint(
                            date=date.fromisoformat(row["date"]),
                            close=float(row["close"]),
                        )
                    )
                except (TypeError, ValueError) as exc:
                    raise MarketDataError(f"Invalid row in AkShare cache: {cache_path}") from exc
        if not points:
            raise MarketDataError(f"Empty AkShare cache file: {cache_path}")
        points.sort(key=lambda point: point.date)
        return PriceSeries(asset_name=asset_name, points=points)

    def _write_cache(self, cache_path: Path, series: PriceSeries) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["date", "asset_name", "close"])
            writer.writeheader()
            for point in series.points:
                writer.writerow(
                    {
                        "date": point.date.isoformat(),
                        "asset_name": series.asset_name,
                        "close": point.close,
                    }
                )

    def _cache_path(
        self,
        asset_name: str,
        provider_type: str,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Path:
        safe_asset = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", asset_name)
        safe_symbol = re.sub(r"[^0-9A-Za-z_-]+", "_", symbol)
        filename = f"{safe_asset}_{provider_type}_{safe_symbol}_{start_date}_{end_date}.csv"
        return self.cache_dir / filename

    def _rough_end_date(self, start_date: str, horizon: str) -> str:
        horizon_days = {"T+1": 8, "T+3": 14, "T+7": 21}
        if horizon not in horizon_days:
            raise MarketDataError(f"Unsupported horizon: {horizon}")
        return (date.fromisoformat(start_date) + timedelta(days=horizon_days[horizon])).isoformat()

    def _resolve_path(self, path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return PROJECT_ROOT / resolved

    def _compact_date(self, value: str) -> str:
        return date.fromisoformat(value).strftime("%Y%m%d")

    def _find_column(self, df: pd.DataFrame, candidates: list[str]) -> str | None:
        normalized = {str(column).lower(): column for column in df.columns}
        for candidate in candidates:
            if candidate.lower() in normalized:
                return normalized[candidate.lower()]
        return None

    @contextmanager
    def _proxy_env_disabled_if_needed(self):
        """Temporarily disable proxies for AkShare internals when requested.

        On Windows, requests can discover proxies from system settings even when
        HTTP_PROXY/HTTPS_PROXY are empty. AkShare uses plain requests calls
        internally, so --no-proxy needs to suppress both env vars and requests'
        environment proxy merge.
        """
        if self.trust_env:
            yield
            return

        proxy_keys = [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "no_proxy",
        ]
        previous = {key: os.environ.get(key) for key in proxy_keys}
        original_merge = requests.sessions.Session.merge_environment_settings

        def no_proxy_merge(session, url, proxies, stream, verify, cert):
            settings = original_merge(session, url, proxies, stream, verify, cert)
            settings["proxies"] = {}
            return settings

        try:
            for key in proxy_keys:
                os.environ.pop(key, None)
            requests.sessions.Session.merge_environment_settings = no_proxy_merge
            yield
        finally:
            requests.sessions.Session.merge_environment_settings = original_merge
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
