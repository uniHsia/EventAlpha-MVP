"""Tests for official evidence heuristic."""

from __future__ import annotations

from eventalpha.news import (
    ClusterClaim,
    EventCluster,
    NewsItem,
    OfficialEvidenceHeuristic,
    SourceCredibility,
)


def _cluster(title: str) -> EventCluster:
    item = NewsItem(title=title, source="Reuters", source_type="mainstream_media")
    return EventCluster(canonical_title=title, items=[item])


def test_official_evidence_detects_official_source_present() -> None:
    """Official source classification should be strongest signal."""
    status = OfficialEvidenceHeuristic().evaluate(
        _cluster("Commerce Department announces AI chip rules"),
        [SourceCredibility(source_name="Commerce Department", source_type="official_source", credibility_tier="high")],
        [],
    )

    assert status == "official_source_present"


def test_official_evidence_detects_media_reported_official_claim() -> None:
    """Media-reported official wording should be detected."""
    cluster = _cluster("Reuters says Commerce Department announces AI chip rules")
    claim = ClusterClaim(claim_text=cluster.canonical_title, supporting_sources=["Reuters"])

    status = OfficialEvidenceHeuristic().evaluate(
        cluster,
        [SourceCredibility(source_name="Reuters", source_type="mainstream_media", credibility_tier="high")],
        [claim],
    )

    assert status == "official_claim_reported_by_media"


def test_official_evidence_no_official_signal() -> None:
    """No official source or marker should stay no_official_evidence."""
    status = OfficialEvidenceHeuristic().evaluate(
        _cluster("AI chip market analysis update"),
        [SourceCredibility(source_name="Random Blog", source_type="blog_or_unknown", credibility_tier="unknown")],
        [],
    )

    assert status == "no_official_evidence"
