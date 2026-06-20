"""Tests for EventCluster schema."""

from __future__ import annotations

from datetime import datetime, timezone

from eventalpha.news import EventCluster, NewsItem, make_cluster_id


def _item(title: str, source: str, at: datetime) -> NewsItem:
    return NewsItem(
        title=title,
        source=source,
        source_type="mainstream_media",
        published_at=at,
    )


def test_event_cluster_can_be_created_with_derived_fields() -> None:
    """EventCluster should fill stable ID, sources, counts, and seen window."""
    older = datetime(2024, 6, 17, 8, tzinfo=timezone.utc)
    newer = datetime(2024, 6, 17, 10, tzinfo=timezone.utc)
    first = _item("AI chip export controls expand", "Reuters", older)
    second = _item("US AI chip controls affect GPU shipments", "Bloomberg", newer)

    cluster = EventCluster(canonical_title=first.title, items=[first, second])

    assert cluster.cluster_id == make_cluster_id([second, first])
    assert cluster.sources == ["Reuters", "Bloomberg"]
    assert cluster.source_count == 2
    assert cluster.first_seen_at == older
    assert cluster.last_seen_at == newer


def test_event_cluster_id_is_stable_across_item_order() -> None:
    """Cluster ID should be independent of item ordering."""
    at = datetime(2024, 6, 17, 8, tzinfo=timezone.utc)
    first = _item("AI chip export controls expand", "Reuters", at)
    second = _item("US AI chip controls affect GPU shipments", "Bloomberg", at)

    assert make_cluster_id([first, second]) == make_cluster_id([second, first])
