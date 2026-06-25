from __future__ import annotations

from eventalpha.news import EventCluster, NewsItem, normalize_cluster_credibility
from eventalpha.news.schemas import ClusterCredibilityReport


def _cluster(
    *,
    source_count: int,
    cluster_type: str,
    title: str = "AI chip export control update",
) -> EventCluster:
    items = [
        NewsItem(
            title=title,
            source=f"Source {index}",
            source_type="mainstream_media",
        )
        for index in range(source_count)
    ]
    sources = [item.source for item in items]
    return EventCluster(
        canonical_title=title,
        items=items,
        sources=sources,
        source_count=source_count,
        item_count=len(items),
        unique_source_count=source_count,
        cluster_type=cluster_type,
        mainstream_source_count=source_count,
        independent_confirmation=source_count >= 2,
    )


def _report(official: str, consistency: str = "consistent", risk_flags: list[str] | None = None) -> ClusterCredibilityReport:
    return ClusterCredibilityReport(
        cluster_id="CLUSTER_1",
        credibility_score=0.5,
        credibility_status="placeholder",
        consistency_status=consistency,
        official_evidence_status=official,
        risk_flags=risk_flags or [],
        verification_notes=[],
        source_summary=[],
        claims=[],
    )


def test_single_source_no_official_maps_low_confidence() -> None:
    normalized = normalize_cluster_credibility(
        _cluster(source_count=1, cluster_type="single_news_event"),
        _report("no_official_evidence"),
    )
    assert normalized.verification_status == "single_source_low_confidence"
    assert normalized.credibility_score <= 0.45


def test_single_source_official_maps_official_single_source() -> None:
    normalized = normalize_cluster_credibility(
        _cluster(source_count=1, cluster_type="single_news_event"),
        _report("official_source_present"),
    )
    assert normalized.verification_status == "official_single_source"
    assert 0.45 <= normalized.credibility_score <= 0.65


def test_multi_source_no_official_maps_multi_source_observed() -> None:
    normalized = normalize_cluster_credibility(
        _cluster(source_count=2, cluster_type="multi_source_event"),
        _report("no_official_evidence"),
    )
    assert normalized.verification_status == "multi_source_observed"
    assert 0.60 <= normalized.credibility_score <= 0.75


def test_multi_source_official_maps_confirmed() -> None:
    normalized = normalize_cluster_credibility(
        _cluster(source_count=3, cluster_type="official_update_cluster"),
        _report("official_source_present"),
    )
    assert normalized.verification_status == "confirmed"
    assert normalized.credibility_score >= 0.75


def test_conflict_maps_conflict_detected() -> None:
    normalized = normalize_cluster_credibility(
        _cluster(source_count=2, cluster_type="multi_source_event"),
        _report("no_official_evidence", consistency="conflicting_claim", risk_flags=["conflicting"]),
    )
    assert normalized.verification_status == "conflict_detected"
    assert normalized.credibility_score <= 0.50


def test_analysis_cluster_maps_analysis_only() -> None:
    normalized = normalize_cluster_credibility(
        _cluster(source_count=1, cluster_type="analysis_digest", title="Semiconductor Engineering analysis digest"),
        _report("no_official_evidence"),
    )
    assert normalized.verification_status == "analysis_only"
    assert normalized.credibility_score <= 0.45
