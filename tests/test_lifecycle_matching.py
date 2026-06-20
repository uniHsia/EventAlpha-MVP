"""Tests for event lifecycle matching."""

from __future__ import annotations

from eventalpha.news import (
    ClusterClaim,
    ClusterCredibilityReport,
    EventCluster,
    EventLifecycleMatcher,
    NewsItem,
    TrackedEvent,
)
from eventalpha.schemas.base import utc_now


def _cluster(title: str, cluster_id: str = "", keywords: list[str] | None = None) -> EventCluster:
    return EventCluster(
        cluster_id=cluster_id,
        canonical_title=title,
        items=[
            NewsItem(
                title=title,
                source="Reuters",
                source_type="mainstream_media",
                url=f"mock://{title}",
            )
        ],
        sources=["Reuters"],
        source_count=1,
        dominant_keywords=keywords or ["technology", "export"],
    )


def _report(cluster: EventCluster, status: str = "single_source_low_confidence") -> ClusterCredibilityReport:
    return ClusterCredibilityReport(
        cluster_id=cluster.cluster_id,
        credibility_score=0.3,
        credibility_status=status,
        claims=[
            ClusterClaim(
                claim_text=cluster.canonical_title,
                supporting_item_ids=[item.news_id for item in cluster.items],
                supporting_sources=["Reuters"],
            )
        ],
        consistency_status="single_source_claim",
        official_evidence_status="no_official_evidence",
    )


def _tracked(title: str, cluster_ids: list[str] | None = None, stage: str = "developing") -> TrackedEvent:
    now = utc_now()
    return TrackedEvent(
        canonical_title=title,
        lifecycle_stage=stage,
        first_seen_at=now,
        last_seen_at=now,
        cluster_ids=cluster_ids or [],
        sources=["Reuters"],
        source_count=1,
        latest_claims=[title],
        dominant_keywords=["technology", "export"],
    )


def test_similar_cluster_matches_existing_event() -> None:
    cluster = _cluster("US expands AI chip export controls on advanced GPU sales")
    existing = _tracked("US expands AI chip export controls for advanced GPUs")

    match = EventLifecycleMatcher().match(cluster, _report(cluster), [existing])

    assert match.matched is True
    assert match.tracked_event_id == existing.tracked_event_id


def test_unrelated_cluster_does_not_match() -> None:
    cluster = _cluster("Middle East conflict raises oil supply concerns", keywords=["conflict", "oil"])
    existing = _tracked("US expands AI chip export controls for advanced GPUs")

    match = EventLifecycleMatcher().match(cluster, _report(cluster), [existing])

    assert match.matched is False


def test_same_cluster_id_forces_match() -> None:
    cluster = _cluster("Different wording for same event", cluster_id="CLUSTER_SHARED")
    existing = _tracked("Older title", cluster_ids=["CLUSTER_SHARED"])

    match = EventLifecycleMatcher().match(cluster, _report(cluster), [existing])

    assert match.matched is True
    assert match.score == 1.0


def test_analysis_only_does_not_easily_merge_with_factual_event() -> None:
    cluster = _cluster("The China chip strategy that is backfiring on America", keywords=["technology"])
    existing = _tracked("US expands AI chip export controls for advanced GPUs", stage="developing")

    match = EventLifecycleMatcher().match(cluster, _report(cluster, status="analysis_only"), [existing])

    assert match.matched is False
