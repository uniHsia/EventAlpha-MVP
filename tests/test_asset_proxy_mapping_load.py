"""Asset proxy mapping load tests."""

from __future__ import annotations

from eventalpha.data_sources import ProviderRouter


def test_asset_proxy_mapping_loads_rules() -> None:
    """Proxy mapping YAML should load into Pydantic rules."""
    router = ProviderRouter()

    rule = router.proxy_rules["ai_export_control"]

    assert rule.event_type == "ai_export_control"
    assert rule.candidates
    assert rule.candidates[0].asset_name == "国产 AI 芯片"
    assert rule.candidates[0].proxy_asset_name == "中证人工智能主题指数"
    assert rule.candidates[0].provider == "akshare"
    assert any(
        candidate.proxy_asset_name == "国产 AI 芯片"
        and candidate.provider == "csv"
        for candidate in rule.candidates
    )


def test_unverified_assets_are_not_marked_verified() -> None:
    """Uncertain real proxies must remain unverified or missing."""
    router = ProviderRouter()
    earthquake_rule = router.proxy_rules["earthquake_supply_chain"]

    japanese_materials = [
        candidate
        for candidate in earthquake_rule.candidates
        if candidate.asset_name == "日本半导体材料"
    ][0]

    assert japanese_materials.mapping_status == "unverified"
    assert japanese_materials.mapping_status != "verified"
