"""Tests for Phase 4A news schemas."""

from __future__ import annotations

from eventalpha.news import NewsFetchResult, NewsItem, make_news_id


def test_news_item_defaults_and_stable_url_id() -> None:
    """NewsItem should create stable IDs from URLs and safe defaults."""
    first = NewsItem(
        title="AI chip export controls expand",
        url="https://example.com/news/ai-chip",
        source="Example Wire",
    )
    second = NewsItem(
        title="Different title for same URL",
        url="https://example.com/news/ai-chip/",
        source="Another Wire",
    )

    assert first.news_id == second.news_id
    assert first.source_type == "unknown"
    assert first.tags == []
    assert first.fetched_at is not None


def test_news_id_falls_back_to_source_title_hash() -> None:
    """Items without URLs should derive IDs from normalized source/title."""
    first = make_news_id("  Rate   cut announced  ", "Central Bank")
    second = make_news_id("rate cut announced", "central bank")

    assert first == second
    assert first.startswith("NEWS_")


def test_news_fetch_result_can_collect_items_and_errors() -> None:
    """Provider result schema should carry partial data and source errors."""
    item = NewsItem(title="Tariff policy update", source="Mock")
    result = NewsFetchResult(
        source_name="mock",
        items=[item],
        errors=["one provider warning"],
    )

    assert result.items == [item]
    assert result.errors == ["one provider warning"]
    assert result.fetched_at is not None
