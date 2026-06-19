"""AkShare provider mapping tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventalpha.data_sources import AkShareMarketDataProvider
from eventalpha.schemas import MarketDataError


def test_akshare_provider_reads_mapping() -> None:
    """AkShareProvider should read akshare assets from asset_code_mapping.yaml."""
    provider = AkShareMarketDataProvider()

    config = provider.get_asset_config("沪深300")

    assert config["provider"] == "akshare"
    assert config["provider_type"] == "index"
    assert config["provider_symbol"] == "000300"
    assert config["eastmoney_secid"] == "1.000300"


def test_missing_mapping_raises_market_data_error() -> None:
    """Missing asset mapping should fail with a clear MarketDataError."""
    provider = AkShareMarketDataProvider()

    with pytest.raises(MarketDataError, match="No asset mapping"):
        provider.get_asset_config("不存在的 AkShare 资产")


def test_non_akshare_mapping_raises_market_data_error() -> None:
    """CSV-only assets should not be silently fetched from AkShare."""
    provider = AkShareMarketDataProvider()

    with pytest.raises(MarketDataError, match="not akshare"):
        provider.get_asset_config("国产 AI 芯片")
