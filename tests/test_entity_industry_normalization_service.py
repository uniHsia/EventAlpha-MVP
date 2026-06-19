"""Tests for entity and industry normalization."""

from __future__ import annotations

from eventalpha.services import EntityNormalizationService, IndustryNormalizationService


def test_entity_normalization_aliases() -> None:
    """Entity aliases should normalize independently from assets."""
    service = EntityNormalizationService()

    assert service.normalize_entity_name("央行") == "中国人民银行"
    assert service.normalize_entity_name("AI芯片") == "AI 芯片"
    assert service.normalize_entity_name("原油价格") == "原油"
    assert service.normalize_entity_name("避险资产") == "黄金"
    assert service.normalize_entity_name("加征关税") == "关税"
    assert service.normalize_entity_name("强震") == "地震"


def test_entity_unknown_preserved() -> None:
    """Unknown entities should be preserved and warned."""
    service = EntityNormalizationService()

    assert service.normalize_entity_list(["未知机构"]) == ["未知机构"]
    assert service.warnings == ["Unknown entity alias preserved: 未知机构"]


def test_industry_normalization_aliases() -> None:
    """Industry aliases should normalize to industry labels."""
    service = IndustryNormalizationService()

    assert service.normalize_industry_name("石油") == "能源"
    assert service.normalize_industry_name("原油") == "能源"
    assert service.normalize_industry_name("石油天然气") == "能源"
    assert service.normalize_industry_name("黄金") == "贵金属"
    assert service.normalize_industry_name("美元") == "汇率"
    assert service.normalize_industry_name("成长风格") == "权益市场"


def test_industry_unknown_preserved() -> None:
    """Unknown industries should be preserved and warned."""
    service = IndustryNormalizationService()

    assert service.normalize_industry_list(["未知行业"]) == ["未知行业"]
    assert service.warnings == ["Unknown industry alias preserved: 未知行业"]
