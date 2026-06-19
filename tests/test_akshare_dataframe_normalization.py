"""AkShare DataFrame normalization tests."""

from __future__ import annotations

import pandas as pd
import pytest

from eventalpha.data_sources import AkShareMarketDataProvider
from eventalpha.schemas import MarketDataError


def test_normalizes_chinese_date_and_close_columns(tmp_path) -> None:
    """Chinese AkShare columns should normalize to PriceSeries."""
    provider = AkShareMarketDataProvider(cache_dir=tmp_path)
    df = pd.DataFrame(
        {
            "日期": ["2026-06-19", "2026-06-18", "2026-06-22"],
            "收盘": [101, 100, None],
        }
    )

    series = provider._normalize_akshare_dataframe(df, "沪深300")

    assert series.asset_name == "沪深300"
    assert [point.date.isoformat() for point in series.points] == [
        "2026-06-18",
        "2026-06-19",
    ]
    assert [point.close for point in series.points] == [100.0, 101.0]


def test_missing_dataframe_columns_raise_error(tmp_path) -> None:
    """Missing date or close columns should raise MarketDataError."""
    provider = AkShareMarketDataProvider(cache_dir=tmp_path)
    df = pd.DataFrame({"日期": ["2026-06-18"], "开盘": [100]})

    with pytest.raises(MarketDataError, match="收盘/close"):
        provider._normalize_akshare_dataframe(df, "沪深300")
