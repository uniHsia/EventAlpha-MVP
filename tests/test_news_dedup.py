"""Tests for news deduplication."""

from __future__ import annotations

from eventalpha.news import NewsItem, deduplicate_news


def test_news_dedup_uses_normalized_url() -> None:
    """Same URL should keep only the first item."""
    first = NewsItem(title="AI chip export control", url="https://example.com/a/", source="A")
    duplicate = NewsItem(title="Different headline", url="https://example.com/a", source="B")

    result = deduplicate_news([first, duplicate])

    assert result.items == [first]
    assert result.before_count == 2
    assert result.after_count == 1
    assert result.duplicate_count == 1


def test_news_dedup_falls_back_to_title_key_without_url() -> None:
    """No-URL items should dedupe by normalized title."""
    first = NewsItem(title="  Central   bank cuts rates ", source="A")
    duplicate = NewsItem(title="central bank cuts rates", source="B")

    result = deduplicate_news([first, duplicate])

    assert result.items == [first]
    assert result.duplicate_count == 1
