"""Rule-based claim extraction from event clusters."""

from __future__ import annotations

import re

from .schemas import ClusterClaim, EventCluster


UNCERTAINTY_MARKERS = ("weighs", "mulls", "considering", "reportedly", "rumor", "尚未确认", "考虑", "拟", "传闻")
ANALYSIS_MARKERS = ("strategy", "opinion", "analysis", "backfiring", "missing piece", "explains", "why")
OFFICIAL_MARKERS = ("announces", "says", "ministry", "central bank", "official", "商务部", "央行", "宣布")
MARKET_MARKERS = ("market", "shares", "stocks", "prices", "yields", "oil", "gold")
CONFLICT_MARKERS = ("denies", "rejects", "false", "辟谣", "否认")


class ClusterClaimExtractor:
    """Extract lightweight claims from cluster titles and summaries."""

    def extract(self, cluster: EventCluster) -> list[ClusterClaim]:
        """Return at least one claim for a cluster."""
        text = _clean_claim_text(cluster.canonical_title)
        supporting_item_ids = [item.news_id for item in cluster.items]
        supporting_sources = _unique([item.source for item in cluster.items])
        claim_type = _claim_type(text)
        uncertainty_markers = _find_markers(text, UNCERTAINTY_MARKERS)
        contradicting_ids = [
            item.news_id
            for item in cluster.items
            if _find_markers(f"{item.title} {item.summary or ''}", CONFLICT_MARKERS)
        ]
        return [
            ClusterClaim(
                claim_text=text,
                claim_type=claim_type,
                supporting_item_ids=supporting_item_ids,
                supporting_sources=supporting_sources,
                contradicting_item_ids=contradicting_ids,
                uncertainty_markers=uncertainty_markers,
            )
        ]


def _claim_type(text: str) -> str:
    if _find_markers(text, UNCERTAINTY_MARKERS):
        return "policy_considering"
    if _find_markers(text, OFFICIAL_MARKERS):
        return "official_announcement"
    if _find_markers(text, ANALYSIS_MARKERS):
        return "analysis_opinion"
    if _find_markers(text, MARKET_MARKERS):
        return "market_reaction"
    return "event_fact"


def _find_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [marker for marker in markers if marker.casefold() in lowered]


def _clean_claim_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _unique(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
