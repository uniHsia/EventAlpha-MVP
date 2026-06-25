from __future__ import annotations

from eventalpha.news import EventCluster, NewsItem
from eventalpha.news.schemas import ClusterCredibilityReport
from scripts.run_event_cluster_scout import rank_event_candidates


def _cluster(cluster_id: str, cluster_type: str, confidence: float, event_type: str) -> EventCluster:
    item = NewsItem(
        title=f"{cluster_id} title",
        source="Reuters",
        source_type="mainstream_media",
    )
    return EventCluster(
        cluster_id=cluster_id,
        canonical_title=item.title,
        items=[item],
        sources=[item.source],
        source_count=1 if cluster_type == "analysis_digest" else 2,
        item_count=1,
        unique_source_count=1 if cluster_type == "analysis_digest" else 2,
        mainstream_source_count=1,
        candidate_event_type=event_type,
        cluster_type=cluster_type,
        independent_confirmation=cluster_type != "analysis_digest",
        confidence=confidence,
    )


def _report(cluster_id: str, official: str) -> ClusterCredibilityReport:
    return ClusterCredibilityReport(
        cluster_id=cluster_id,
        credibility_score=0.7,
        credibility_status="placeholder",
        source_summary=[],
        claims=[],
        consistency_status="consistent",
        official_evidence_status=official,
        risk_flags=[],
        verification_notes=[],
    )


def test_official_multi_source_ranks_ahead_of_analysis_digest() -> None:
    strong = _cluster("CLUSTER_A", "multi_source_event", 0.8, "ai_export_control")
    weak = _cluster("CLUSTER_B", "analysis_digest", 0.8, "unknown")
    ranked = rank_event_candidates(
        [weak, strong],
        {
            "CLUSTER_A": _report("CLUSTER_A", "official_source_present"),
            "CLUSTER_B": _report("CLUSTER_B", "no_official_evidence"),
        },
    )
    assert ranked[0]["cluster"].cluster_id == "CLUSTER_A"
    assert ranked[0]["candidate_priority"] > ranked[1]["candidate_priority"]
