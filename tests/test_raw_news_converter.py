"""Tests for NewsItem to RawNews conversion."""

from __future__ import annotations

from datetime import datetime, timezone

from eventalpha.news import NewsItem, news_item_to_raw_news


def test_news_item_to_raw_news_preserves_source_and_metadata() -> None:
    """Collected news should be convertible into existing RawNews without schema changes."""
    published_at = datetime(2024, 6, 17, 10, 0, tzinfo=timezone.utc)
    item = NewsItem(
        title="AI chip export controls expand",
        summary="Advanced GPU restrictions affect the semiconductor supply chain.",
        url="https://example.com/ai-chip",
        source="Example Wire",
        source_type="mainstream_media",
        published_at=published_at,
        language="en",
        country="US",
        tags=["mock", "filter:technology"],
    )

    raw_news = news_item_to_raw_news(item)

    assert raw_news.raw_id == item.news_id
    assert raw_news.title == item.title
    assert raw_news.source == "Example Wire"
    assert raw_news.source_type == "mainstream_media"
    assert raw_news.publish_time == published_at
    assert raw_news.raw_text == item.summary
    assert raw_news.url == item.url
    assert raw_news.metadata["news_id"] == item.news_id
    assert raw_news.metadata["url"] == item.url
    assert raw_news.metadata["tags"] == "mock,filter:technology"
