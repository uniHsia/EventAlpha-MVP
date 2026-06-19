"""Tests for asset alias normalization."""

from __future__ import annotations

from eventalpha.services import AssetNormalizationService


def test_alias_normalizes_to_standard_asset_name() -> None:
    """Known aliases should normalize to system standard asset names."""
    service = AssetNormalizationService()

    assert service.normalize_asset_name("AI芯片") == "国产 AI 芯片"
    assert service.normalize_asset_name("国产EDA") == "国产 EDA"
    assert service.normalize_asset_name("AI 服务器") == "服务器"


def test_unknown_asset_is_preserved_with_warning() -> None:
    """Unknown assets should not be silently deleted."""
    service = AssetNormalizationService()

    assert service.normalize_asset_name("未知主题") == "未知主题"
    assert service.warnings == ["Unknown asset alias preserved: 未知主题"]


def test_normalize_asset_list_deduplicates_and_preserves_order() -> None:
    """List normalization should dedupe without reordering."""
    service = AssetNormalizationService()

    result = service.normalize_asset_list(["AI芯片", "国产 AI 芯片", "EDA", "未知主题"])

    assert result == ["国产 AI 芯片", "国产 EDA", "未知主题"]
    assert service.warnings == ["Unknown asset alias preserved: 未知主题"]

