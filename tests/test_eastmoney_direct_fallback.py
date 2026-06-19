"""EastMoney direct fallback tests for AkShareProvider."""

from __future__ import annotations

import pandas as pd
import pytest

from eventalpha.data_sources import AkShareMarketDataProvider
from eventalpha.schemas import MarketDataError


def test_eastmoney_secid_uses_direct_fetch(tmp_path, monkeypatch) -> None:
    """Assets with eastmoney_secid should bypass AkShare's index mapping call."""
    provider = AkShareMarketDataProvider(cache_dir=tmp_path)
    calls = {"direct": 0}

    def fake_direct(secid, start_date, end_date, asset_name):
        calls["direct"] += 1
        assert secid == "1.000300"
        assert asset_name == "沪深300"
        return pd.DataFrame(
            {
                "日期": ["2024-06-18", "2024-06-19"],
                "收盘": [3500, 3510],
            }
        )

    def fail_akshare(provider_type, symbol, start_date, end_date):
        pytest.fail("AkShare fetch should not be called when eastmoney_secid exists")

    monkeypatch.setattr(provider, "_fetch_eastmoney_direct_dataframe", fake_direct)
    monkeypatch.setattr(provider, "_fetch_akshare_dataframe", fail_akshare)

    series = provider.get_price_series("沪深300", "2024-06-18", "2024-06-25")

    assert calls["direct"] == 1
    assert [point.close for point in series.points] == [3500.0, 3510.0]


def test_provider_can_disable_proxy_environment(tmp_path) -> None:
    """Provider should allow direct EastMoney requests to ignore proxy env."""
    provider = AkShareMarketDataProvider(cache_dir=tmp_path, trust_env=False)

    assert provider.trust_env is False


def test_normalizes_eastmoney_kline_payload(tmp_path) -> None:
    """EastMoney kline JSON should convert to the same DataFrame columns."""
    provider = AkShareMarketDataProvider(cache_dir=tmp_path)
    payload = {
        "data": {
            "klines": [
                "2024-06-18,3533.49,3545.59,3551.71,3532.78,123",
                "2024-06-19,3543.36,3528.75,3543.36,3520.11,123",
            ]
        }
    }

    df = provider._normalize_eastmoney_kline_payload(payload, "沪深300", "1.000300")
    series = provider._normalize_akshare_dataframe(df, "沪深300")

    assert [point.date.isoformat() for point in series.points] == [
        "2024-06-18",
        "2024-06-19",
    ]
    assert [point.close for point in series.points] == [3545.59, 3528.75]


def test_empty_eastmoney_kline_payload_raises(tmp_path) -> None:
    """Empty EastMoney kline payload should raise a clear MarketDataError."""
    provider = AkShareMarketDataProvider(cache_dir=tmp_path)

    with pytest.raises(MarketDataError, match="has no klines"):
        provider._normalize_eastmoney_kline_payload({"data": {"klines": []}}, "沪深300", "1.000300")
