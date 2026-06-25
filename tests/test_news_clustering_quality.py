from __future__ import annotations

from datetime import datetime, timezone

from eventalpha.news import NewsClusterer, NewsItem


def test_same_source_semiconductor_engineering_articles_do_not_merge_as_multi_source_event() -> None:
    now = datetime(2026, 6, 25, tzinfo=timezone.utc)
    items = [
        NewsItem(
            title="Why advanced packaging matters for AI accelerators",
            summary="Semiconductor Engineering analysis on packaging trends.",
            source="Semiconductor Engineering",
            source_type="research_report",
            published_at=now,
        ),
        NewsItem(
            title="Chiplet test strategy evolves for next-generation CPUs",
            summary="Semiconductor Engineering feature on test methodology.",
            source="Semiconductor Engineering",
            source_type="research_report",
            published_at=now,
        ),
    ]
    clusters = NewsClusterer().cluster(items)
    assert all(cluster.cluster_type in {"analysis_digest", "same_source_topic_cluster", "single_news_event"} for cluster in clusters)
    assert all(cluster.unique_source_count == 1 for cluster in clusters)
    assert all(cluster.cluster_type != "multi_source_event" for cluster in clusters)
