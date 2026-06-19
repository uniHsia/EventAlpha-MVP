"""ProviderRouter resolution tests."""

from __future__ import annotations

import pytest

from eventalpha.data_sources import ProviderRouter
from eventalpha.schemas import MarketDataError


def test_event_specific_mapping_takes_priority() -> None:
    """Event-specific proxy mapping should be used before asset_code_mapping."""
    router = ProviderRouter(default_event_type="ai_export_control")

    route = router.resolve_asset("国产 AI 芯片")

    assert route.route_source == "event_proxy"
    assert route.provider == "csv"
    assert route.proxy_asset_name == "国产 AI 芯片"
    assert route.mapping_status == "candidate"


def test_fallback_to_asset_code_mapping() -> None:
    """Assets without event-specific rules should fall back to asset_code_mapping."""
    router = ProviderRouter()

    route = router.resolve_asset("沪深300")

    assert route.route_source == "asset_code"
    assert route.provider == "akshare"
    assert route.provider_symbol == "000300"
    assert route.mapping_status == "verified"


def test_missing_mapping_raises_market_data_error() -> None:
    """Unknown assets should fail clearly."""
    router = ProviderRouter()

    with pytest.raises(MarketDataError, match="No provider mapping"):
        router.resolve_asset("不存在的资产")


def test_missing_event_proxy_raises_market_data_error() -> None:
    """Explicit missing mappings should not be executable."""
    router = ProviderRouter(default_event_type="geopolitical_conflict")

    with pytest.raises(MarketDataError, match="尚未确认|Provider missing|not executable"):
        router.resolve_asset("航空")


def test_unverified_mapping_requires_opt_in() -> None:
    """Unverified mappings should be blocked unless explicitly allowed."""
    router = ProviderRouter(default_event_type="earthquake_supply_chain")

    with pytest.raises(MarketDataError, match="not allowed"):
        router.resolve_asset("日本半导体材料")

    allowed_router = ProviderRouter(
        default_event_type="earthquake_supply_chain",
        allow_unverified=True,
    )
    route = allowed_router.resolve_asset("日本半导体材料")

    assert route.mapping_status == "unverified"
    assert route.is_usable is True
