"""Tests for event lifecycle update rules."""

from __future__ import annotations

from datetime import timedelta

from eventalpha.news import (
    ClusterClaim,
    ClusterCredibilityReport,
    EventCluster,
    EventLifecycleUpdater,
    NewsItem,
    TrackedEvent,
)
from eventalpha.schemas.base import utc_now


def _cluster(title: str, source: str = "Reuters", source_count: int = 1) -> EventCluster:
    items = [
        NewsItem(
            title=title,
            source=source,
            source_type="mainstream_media",
            url=f"mock://{source}/{title}",
        )
    ]
    if source_count > 1:
        items.append(
            NewsItem(
                title=title,
                source="Bloomberg",
                source_type="mainstream_media",
                url=f"mock://bloomberg/{title}",
            )
        )
    return EventCluster(
        canonical_title=title,
        canonical_summary=f"Summary for {title}",
        items=items,
        sources=[item.source for item in items],
        source_count=len(items),
        dominant_keywords=["technology", "export"],
    )


def _report(
    cluster: EventCluster,
    status: str = "single_source_low_confidence",
    official: str = "no_official_evidence",
    consistency: str = "single_source_claim",
) -> ClusterCredibilityReport:
    return ClusterCredibilityReport(
        cluster_id=cluster.cluster_id,
        credibility_score=0.8 if status == "high_confidence" else 0.3,
        credibility_status=status,
        claims=[
            ClusterClaim(
                claim_text=cluster.canonical_title,
                supporting_item_ids=[item.news_id for item in cluster.items],
                supporting_sources=cluster.sources,
            )
        ],
        consistency_status=consistency,
        official_evidence_status=official,
    )


def test_new_event_creation_sets_initial_stage() -> None:
    cluster = _cluster("US expands AI chip export controls")

    event, updates = EventLifecycleUpdater().apply(cluster, _report(cluster, status="unconfirmed_or_considering"))

    assert event.lifecycle_stage == "unconfirmed_or_considering"
    assert updates[0].update_type == "new_event"
    assert event.timeline[0].update_type == "new_event"


def test_source_count_increase_is_recorded() -> None:
    initial_cluster = _cluster("US expands AI chip export controls", source_count=1)
    event, _ = EventLifecycleUpdater().apply(initial_cluster, _report(initial_cluster))
    update_cluster = _cluster("US expands AI chip export controls", source_count=2)

    updated, updates = EventLifecycleUpdater().apply(update_cluster, _report(update_cluster), matched_event=event)

    assert updated.source_count == 2
    assert "source_count_increased" in {update.update_type for update in updates}


def test_credibility_upgrade_is_recorded() -> None:
    cluster = _cluster("US expands AI chip export controls")
    event, _ = EventLifecycleUpdater().apply(cluster, _report(cluster))

    updated, updates = EventLifecycleUpdater().apply(cluster, _report(cluster, status="high_confidence"), event)

    assert updated.lifecycle_stage == "confirmed"
    assert "credibility_upgraded" in {update.update_type for update in updates}


def test_official_evidence_added_is_recorded() -> None:
    cluster = _cluster("Central bank announces rate cut")
    event, _ = EventLifecycleUpdater().apply(cluster, _report(cluster))

    _, updates = EventLifecycleUpdater().apply(
        cluster,
        _report(cluster, status="high_confidence", official="official_source_present"),
        event,
    )

    assert "official_evidence_added" in {update.update_type for update in updates}


def test_conflict_detected_sets_conflicting_stage() -> None:
    cluster = _cluster("Ministry denies earlier export control report")
    event, _ = EventLifecycleUpdater().apply(cluster, _report(cluster))

    updated, updates = EventLifecycleUpdater().apply(
        cluster,
        _report(cluster, status="conflicting_claims", consistency="conflicting_claim"),
        event,
    )

    assert updated.lifecycle_stage == "conflicting"
    assert "conflict_detected" in {update.update_type for update in updates}


def test_mark_stale_and_closed() -> None:
    now = utc_now()
    event = TrackedEvent(
        canonical_title="Old event",
        first_seen_at=now - timedelta(days=40),
        last_seen_at=now - timedelta(days=8),
    )
    updater = EventLifecycleUpdater()

    stale_updates = updater.mark_stale([event], now=now)
    closed_updates = updater.mark_stale([event], now=now + timedelta(days=23))

    assert stale_updates[0].update_type == "event_stale"
    assert closed_updates[0].update_type == "event_closed"
    assert event.is_active is False
