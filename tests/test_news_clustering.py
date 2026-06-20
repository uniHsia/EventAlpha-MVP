"""Tests for lightweight news clustering."""

from __future__ import annotations

from eventalpha.news import NewsClusterer, NewsItem


def _item(title: str, source: str = "Mock", url: str | None = None) -> NewsItem:
    return NewsItem(
        title=title,
        summary="AI chip export control and advanced GPU policy update.",
        url=url,
        source=source,
        source_type="mainstream_media",
    )


def test_similar_ai_chip_export_titles_cluster_together() -> None:
    """Similar AI chip export control titles should be grouped."""
    items = [
        _item("US expands AI chip export controls on advanced GPU sales", "Reuters"),
        _item("AI chip export control update affects GPU shipments", "Bloomberg"),
    ]

    clusters = NewsClusterer().cluster(items)

    assert len(clusters) == 1
    assert len(clusters[0].items) == 2
    assert any("keyword overlap" in reason for reason in clusters[0].debug_reasons)


def test_unrelated_news_does_not_cluster() -> None:
    """Different event themes should remain separate."""
    items = [
        _item("US expands AI chip export controls on advanced GPU sales", "Reuters"),
        NewsItem(
            title="Middle East conflict raises oil supply concerns",
            summary="Regional conflict may affect crude logistics.",
            source="AP",
            source_type="mainstream_media",
        ),
    ]

    clusters = NewsClusterer().cluster(items)

    assert len(clusters) == 2


def test_generic_supply_words_do_not_merge_different_events() -> None:
    """Generic supply/affect wording should not merge unrelated themes."""
    items = [
        NewsItem(
            title="US expands AI chip export controls on advanced GPU sales",
            summary="The policy may affect AI chip supply chains and domestic semiconductor substitutes.",
            source="Mock Global News",
            source_type="mainstream_media",
        ),
        NewsItem(
            title="Middle East conflict raises oil supply concerns",
            summary="Red Sea attacks and regional conflict may affect crude oil logistics.",
            source="Mock Wire",
            source_type="mainstream_media",
        ),
    ]

    clusters = NewsClusterer().cluster(items)

    assert len(clusters) == 2


def test_same_url_forces_cluster() -> None:
    """Identical URLs should force items into one cluster."""
    items = [
        _item("AI chip export control update", "Reuters", "https://example.com/a"),
        _item("Different wording for same article", "Bloomberg", "https://example.com/a/"),
    ]

    clusters = NewsClusterer().cluster(items)

    assert len(clusters) == 1
    assert any("url match" in reason for reason in clusters[0].debug_reasons)


def test_shared_core_keywords_cluster_when_jaccard_is_strict() -> None:
    """Short titles with several shared core terms should still cluster."""
    items = [
        NewsItem(
            title="Taiwan mulls AI chip export curbs to China",
            summary="Taiwan may align AI chip exports policy with US rules.",
            source="Bloomberg",
            source_type="mainstream_media",
        ),
        NewsItem(
            title="Taiwan weighs tighter rules for AI chip exports",
            summary="Taiwan weighs AI chip export rules for China shipments.",
            source="UPI",
            source_type="mainstream_media",
        ),
    ]

    clusters = NewsClusterer().cluster(items)

    assert len(clusters) == 1
    assert any("keyword overlap" in reason for reason in clusters[0].debug_reasons)
