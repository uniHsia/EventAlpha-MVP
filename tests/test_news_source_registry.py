"""Tests for news source registry construction."""

from __future__ import annotations

import pytest

from eventalpha.news import build_real_registry
from eventalpha.news.gdelt_provider import GDELTProvider
from eventalpha.news.rss_provider import RSSProvider


def test_build_real_registry_can_select_rss_only() -> None:
    """RSS-only real registry should skip GDELT when it is rate-limited."""
    registry = build_real_registry(
        source="rss",
        rss_feeds=["https://news.google.com/rss/search?q=AI%20chip"],
    )

    assert len(registry.providers) == 1
    assert isinstance(registry.providers[0], RSSProvider)


def test_build_real_registry_can_select_gdelt_only() -> None:
    """GDELT-only registry should not include RSS providers."""
    registry = build_real_registry(source="gdelt")

    assert len(registry.providers) == 1
    assert isinstance(registry.providers[0], GDELTProvider)
    assert registry.source_entries[0].source_type == "gdelt"


def test_build_real_registry_rejects_unknown_source() -> None:
    """Source selection should fail fast for invalid values."""
    with pytest.raises(ValueError, match="source must be one of"):
        build_real_registry(source="unknown")


def test_build_real_registry_exposes_source_metadata() -> None:
    registry = build_real_registry(
        source="rss",
        rss_feeds=["https://www.sec.gov/news/pressreleases.rss"],
    )

    assert len(registry.source_entries) == 1
    entry = registry.source_entries[0]
    assert entry.source_name == "sec_press_releases"
    assert entry.source_type == "official"
    assert entry.fetch_mode == "rss"
