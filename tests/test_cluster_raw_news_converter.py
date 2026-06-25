"""Tests for EventCluster to RawNews conversion."""

from __future__ import annotations

from eventalpha.news import EventCluster, NewsItem, event_cluster_to_raw_news


def test_event_cluster_to_raw_news_preserves_metadata() -> None:
    """Cluster conversion should preserve source metadata without schema changes."""
    items = [
        NewsItem(
            title="AI chip export control update",
            summary="US policy affects advanced GPU shipments.",
            url="https://example.com/ai",
            source="Reuters",
            source_type="mainstream_media",
            language="en",
        ),
        NewsItem(
            title="AI chip curbs affect GPU exports",
            summary="Chip makers monitor export policy.",
            url="https://example.com/gpu",
            source="Bloomberg",
            source_type="mainstream_media",
            language="en",
        ),
    ]
    cluster = EventCluster(
        canonical_title="AI chip export control update",
        canonical_summary="US policy affects advanced GPU shipments.",
        items=items,
        sources=["Reuters", "Bloomberg"],
        source_count=2,
        item_count=2,
        unique_source_count=2,
        mainstream_source_count=2,
        dominant_keywords=["technology", "export", "control"],
        cluster_type="multi_source_event",
        independent_confirmation=True,
        verification_status="multi_source_observed",
        confidence=0.62,
    )

    raw_news = event_cluster_to_raw_news(cluster)

    assert raw_news.raw_id == cluster.cluster_id
    assert raw_news.title == cluster.canonical_title
    assert raw_news.source == "Reuters, Bloomberg"
    assert raw_news.source_type == "mainstream_media"
    assert raw_news.metadata["cluster_id"] == cluster.cluster_id
    assert raw_news.metadata["source_count"] == "2"
    assert raw_news.metadata["unique_source_count"] == "2"
    assert raw_news.metadata["cluster_type"] == "multi_source_event"
    assert raw_news.metadata["verification_status"] == "multi_source_observed"
    assert "https://example.com/ai" in raw_news.metadata["urls"]
    assert items[0].news_id in raw_news.metadata["item_ids"]
