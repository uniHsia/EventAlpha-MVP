"""Tests for claim consistency summaries."""

from __future__ import annotations

from eventalpha.news import ClaimConsistencyService, ClusterClaim, SourceCredibility


def _claim(text: str, sources: list[str], claim_type: str = "event_fact") -> ClusterClaim:
    return ClusterClaim(
        claim_text=text,
        claim_type=claim_type,
        supporting_item_ids=[f"id-{index}" for index, _ in enumerate(sources)],
        supporting_sources=sources,
    )


def test_claim_consistency_multi_source_consistent() -> None:
    """Multiple sources supporting a claim should be consistent multi-source."""
    summary = [
        SourceCredibility(source_name="Reuters", source_type="mainstream_media", credibility_tier="high"),
        SourceCredibility(source_name="Bloomberg", source_type="financial_media", credibility_tier="high"),
    ]

    result = ClaimConsistencyService().evaluate(
        [_claim("AI chip export controls announced", ["Reuters", "Bloomberg"])],
        summary,
    )

    assert result.status == "consistent_multi_source"
    assert result.high_credibility_source_count == 2


def test_claim_consistency_single_source() -> None:
    """Single-source claims should be labeled as single source."""
    result = ClaimConsistencyService().evaluate([_claim("AI chip export controls announced", ["Reuters"])])

    assert result.status == "single_source_claim"


def test_claim_consistency_analysis_only() -> None:
    """Analysis-only claims should remain distinct from reported facts."""
    result = ClaimConsistencyService().evaluate(
        [_claim("AI export strategy analysis", ["Brookings"], claim_type="analysis_opinion")]
    )

    assert result.status == "analysis_only_claim"
    assert result.analysis_only is True


def test_claim_consistency_conflicting_claim() -> None:
    """Denial/false markers should produce conflicting claim status."""
    claim = _claim("Company denies AI chip export control report", ["Reuters", "Company"])

    result = ClaimConsistencyService().evaluate([claim])

    assert result.status == "conflicting_claim"
