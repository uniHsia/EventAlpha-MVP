"""Tests for source credibility classification."""

from __future__ import annotations

from eventalpha.news import SourceCredibilityRegistry


def test_registry_classifies_mainstream_and_financial_sources() -> None:
    """Known wire/media sources should be high credibility."""
    registry = SourceCredibilityRegistry()

    assert registry.classify("Reuters").source_type == "mainstream_media"
    assert registry.classify("AP").credibility_tier == "high"
    assert registry.classify("BBC News").source_type == "mainstream_media"
    assert registry.classify("Bloomberg.com").source_type == "financial_media"


def test_registry_classifies_think_tank_and_analysis_sources() -> None:
    """Known policy analysis sources should not be treated as primary reporting."""
    registry = SourceCredibilityRegistry()

    brookings = registry.classify("Brookings")
    tech_policy = registry.classify("Tech Policy Press")

    assert brookings.source_type == "think_tank"
    assert brookings.credibility_tier == "medium"
    assert tech_policy.source_type == "analysis_source"


def test_registry_marks_google_news_as_aggregator() -> None:
    """Google News should be marked as aggregator, not original source."""
    source = SourceCredibilityRegistry().classify("Google News", "https://news.google.com/rss")

    assert source.source_type == "aggregator"
    assert source.credibility_tier == "unknown"
    assert "Aggregator" in source.rationale


def test_registry_does_not_mark_extracted_publisher_as_aggregator() -> None:
    """Google News URLs should not override a real extracted publisher name."""
    registry = SourceCredibilityRegistry()

    bloomberg = registry.classify("Bloomberg.com", "https://news.google.com/rss/articles/example")
    nbc = registry.classify("NBC News", "https://news.google.com/rss/articles/example")

    assert bloomberg.source_type == "financial_media"
    assert bloomberg.credibility_tier == "high"
    assert nbc.source_type == "mainstream_media"


def test_registry_keeps_unknown_source_unknown() -> None:
    """Unknown blogs should remain low-information sources."""
    source = SourceCredibilityRegistry().classify("Random Substack Blog")

    assert source.source_type == "blog_or_unknown"
    assert source.credibility_tier == "unknown"
