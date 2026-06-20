"""Rule-based cross-source claim consistency summary."""

from __future__ import annotations

from .claim_extraction import CONFLICT_MARKERS
from .schemas import ClaimConsistencySummary, ClusterClaim, SourceCredibility


class ClaimConsistencyService:
    """Evaluate lightweight consistency status for cluster claims."""

    def evaluate(
        self,
        claims: list[ClusterClaim],
        source_summary: list[SourceCredibility] | None = None,
    ) -> ClaimConsistencySummary:
        """Return consistency summary for claims and source credibility."""
        supporting_sources = sorted({source for claim in claims for source in claim.supporting_sources})
        high_sources = {
            source.source_name
            for source in source_summary or []
            if source.credibility_tier == "high" and source.source_type != "aggregator"
        }
        uncertainty_count = sum(len(claim.uncertainty_markers) for claim in claims)
        analysis_only = bool(claims) and all(claim.claim_type == "analysis_opinion" for claim in claims)
        has_conflict = any(
            claim.contradicting_item_ids
            or any(marker in claim.claim_text.casefold() for marker in CONFLICT_MARKERS)
            for claim in claims
        )

        if has_conflict:
            status = "conflicting_claim"
            rationale = "Contradicting or denial markers were detected."
        elif uncertainty_count:
            status = "unconfirmed_claim"
            rationale = "Uncertainty markers were detected in the claim."
        elif analysis_only:
            status = "analysis_only_claim"
            rationale = "All extracted claims are analysis or opinion."
        elif len(supporting_sources) <= 1:
            status = "single_source_claim"
            rationale = "Claim is supported by only one source."
        else:
            status = "consistent_multi_source"
            rationale = "Similar claim is supported by multiple sources."

        return ClaimConsistencySummary(
            status=status,
            supporting_source_count=len(supporting_sources),
            high_credibility_source_count=len(high_sources & set(supporting_sources)),
            uncertainty_count=uncertainty_count,
            analysis_only=analysis_only,
            rationale=rationale,
        )
