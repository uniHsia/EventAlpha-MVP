"""Tests for entity and industry normalization."""

from __future__ import annotations

from eventalpha.services import EntityNormalizationService, IndustryNormalizationService


def test_entity_normalization_aliases() -> None:
    """Entity aliases should normalize independently from assets."""
    service = EntityNormalizationService()

    assert service.normalize_entity_name("央行") == "中国人民银行"
    assert service.normalize_entity_name("AI芯片") == "AI 芯片"


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
    assert service.normalize_industry_name("黄金") == "贵金属"


def test_industry_unknown_preserved() -> None:
    """Unknown industries should be preserved and warned."""
    service = IndustryNormalizationService()

    assert service.normalize_industry_list(["未知行业"]) == ["未知行业"]
    assert service.warnings == ["Unknown industry alias preserved: 未知行业"]

