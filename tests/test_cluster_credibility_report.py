"""Tests for cluster credibility reports."""

from __future__ import annotations

from eventalpha.news import ClusterCredibilityService, EventCluster, NewsItem


def _cluster(title: str, sources: list[tuple[str, str]] | None = None) -> EventCluster:
    items = [
        NewsItem(title=title, source=source, source_type=source_type)
        for source, source_type in (sources or [("Reuters", "mainstream_media")])
    ]
    return EventCluster(
        canonical_title=title,
        items=items,
        sources=[item.source for item in items],
        source_count=len({item.source for item in items}),
        item_count=len(items),
        unique_source_count=len({item.source for item in items}),
        mainstream_source_count=sum(1 for item in items if item.source_type == "mainstream_media"),
    )


def test_multi_source_high_credibility_cluster_scores_high() -> None:
    """High-quality multi-source official claim should receive high status."""
    cluster = _cluster(
        "Commerce Department announces AI chip export controls",
        [("Reuters", "mainstream_media"), ("Bloomberg", "mainstream_media"), ("AP", "mainstream_media")],
    )

    report = ClusterCredibilityService().evaluate(cluster)

    assert report.credibility_score >= 0.75
    assert report.credibility_status == "high_confidence"


def test_analysis_only_cluster_scores_low() -> None:
    """Analysis-only clusters should be conservative."""
    cluster = _cluster("The missing piece in AI export control strategy", [("Brookings", "research_report")])

    report = ClusterCredibilityService().evaluate(cluster)

    assert report.credibility_status == "analysis_only"
    assert report.credibility_score < 0.4


def test_unconfirmed_cluster_scores_mid_low() -> None:
    """Considering/weighs clusters should remain below high confidence."""
    cluster = _cluster(
        "Taiwan mulls AI chip export curbs",
        [("Bloomberg", "mainstream_media"), ("UPI", "mainstream_media")],
    )

    report = ClusterCredibilityService().evaluate(cluster)

    assert report.credibility_status == "unconfirmed_or_considering"
    assert report.credibility_score < 0.6


def test_conflicting_claims_score_low() -> None:
    """Conflicting claims should receive low credibility."""
    cluster = _cluster(
        "Company denies AI chip export control report",
        [("Reuters", "mainstream_media"), ("Company Blog", "unknown")],
    )

    report = ClusterCredibilityService().evaluate(cluster)

    assert report.credibility_status == "conflicting_claims"
    assert report.credibility_score < 0.3
