"""Tests for cluster verification summaries."""

from __future__ import annotations

from eventalpha.news import ClusterVerificationService, EventCluster, NewsItem


def _cluster(titles_sources: list[tuple[str, str, str]]) -> EventCluster:
    items = [
        NewsItem(
            title=title,
            source=source,
            source_type=source_type,
        )
        for title, source, source_type in titles_sources
    ]
    return EventCluster(
        canonical_title=items[0].title,
        items=items,
        sources=[item.source for item in items],
        source_count=len({item.source for item in items}),
        item_count=len(items),
        unique_source_count=len({item.source for item in items}),
        mainstream_source_count=sum(1 for item in items if item.source_type == "mainstream_media"),
    )


def test_multi_source_supported_status() -> None:
    """Three sources with two mainstream sources should be strongly supported."""
    cluster = _cluster(
        [
            ("AI chip export control update", "Reuters", "mainstream_media"),
            ("AI chip export control update", "Bloomberg", "mainstream_media"),
            ("AI chip export control update", "Policy Daily", "research_report"),
        ]
    )

    verified = ClusterVerificationService().verify(cluster)

    assert verified.verification_status == "multi_source_supported"
    assert verified.confidence >= 0.78
    assert verified.unique_source_count == 3


def test_multi_source_observed_and_single_source_statuses() -> None:
    """Two-source and single-source clusters should get distinct labels."""
    two_source = _cluster(
        [
            ("AI chip export control update", "Reuters", "mainstream_media"),
            ("AI chip export control update", "Policy Daily", "research_report"),
        ]
    )
    single_source = _cluster([("AI chip export control update", "Reuters", "mainstream_media")])

    verifier = ClusterVerificationService()

    assert verifier.verify(two_source).verification_status == "multi_source_observed"
    assert verifier.verify(single_source).verification_status == "single_source"


def test_analysis_only_status() -> None:
    """Think-tank/blog clusters should be marked analysis-only."""
    cluster = _cluster(
        [
            ("AI export control strategy analysis", "Brookings", "research_report"),
            ("The MATCH Act analysis", "Policy Blog", "research_report"),
        ]
    )

    verified = ClusterVerificationService().verify(cluster)

    assert verified.verification_status == "analysis_only"


def test_unconfirmed_or_considering_status_has_priority() -> None:
    """Considering/mulls titles should not become overconfident."""
    cluster = _cluster(
        [
            ("Taiwan mulls AI chip export curbs", "Reuters", "mainstream_media"),
            ("Taiwan weighs tighter AI chip export rules", "Bloomberg", "mainstream_media"),
            ("Taiwan considering AI chip export controls", "AP", "mainstream_media"),
        ]
    )

    verified = ClusterVerificationService().verify(cluster)

    assert verified.verification_status == "unconfirmed_or_considering"
    assert verified.confidence < 0.5
