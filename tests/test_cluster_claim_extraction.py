"""Tests for rule-based cluster claim extraction."""

from __future__ import annotations

from eventalpha.news import ClusterClaimExtractor, EventCluster, NewsItem


def _cluster(title: str, summary: str | None = None) -> EventCluster:
    item = NewsItem(title=title, summary=summary, source="Reuters", source_type="mainstream_media")
    return EventCluster(canonical_title=title, canonical_summary=summary, items=[item])


def test_claim_extractor_detects_uncertainty_markers() -> None:
    """Weighs/mulls/considering should mark policy_considering claims."""
    claims = ClusterClaimExtractor().extract(_cluster("Taiwan mulls AI chip export curbs"))

    assert claims[0].claim_type == "policy_considering"
    assert "mulls" in claims[0].uncertainty_markers


def test_claim_extractor_detects_official_announcement() -> None:
    """Announces/says official wording should mark announcement claims."""
    claims = ClusterClaimExtractor().extract(_cluster("Commerce Department announces AI chip export controls"))

    assert claims[0].claim_type == "official_announcement"


def test_claim_extractor_detects_analysis_opinion() -> None:
    """Strategy/opinion markers should mark analysis claims."""
    claims = ClusterClaimExtractor().extract(_cluster("The missing piece in AI export control strategy"))

    assert claims[0].claim_type == "analysis_opinion"


def test_claim_extractor_always_returns_claim() -> None:
    """Every cluster should produce at least one claim."""
    claims = ClusterClaimExtractor().extract(_cluster("AI chip export control update"))

    assert claims
    assert claims[0].supporting_item_ids
    assert claims[0].supporting_sources == ["Reuters"]
