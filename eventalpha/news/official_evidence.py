"""Official evidence heuristic for event clusters."""

from __future__ import annotations

from .claim_extraction import OFFICIAL_MARKERS
from .schemas import ClusterClaim, EventCluster, SourceCredibility


class OfficialEvidenceHeuristic:
    """Detect official-source or media-reported official evidence signals."""

    def evaluate(
        self,
        cluster: EventCluster,
        source_summary: list[SourceCredibility],
        claims: list[ClusterClaim],
    ) -> str:
        """Return official evidence status without crawling external pages."""
        if any(source.source_type == "official_source" for source in source_summary):
            return "official_source_present"
        combined = " ".join(
            [cluster.canonical_title, cluster.canonical_summary or ""]
            + [claim.claim_text for claim in claims]
            + [item.title for item in cluster.items]
        ).casefold()
        if any(marker.casefold() in combined for marker in OFFICIAL_MARKERS):
            return "official_claim_reported_by_media"
        return "no_official_evidence"
