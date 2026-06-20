"""Cluster-level multi-source credibility pre-verification."""

from __future__ import annotations

from .claim_consistency import ClaimConsistencyService
from .claim_extraction import ClusterClaimExtractor
from .official_evidence import OfficialEvidenceHeuristic
from .schemas import ClusterCredibilityReport, EventCluster, SourceCredibility
from .source_credibility import SourceCredibilityRegistry


class ClusterCredibilityService:
    """Build ClusterCredibilityReport objects from EventCluster inputs."""

    def __init__(
        self,
        source_registry: SourceCredibilityRegistry | None = None,
        claim_extractor: ClusterClaimExtractor | None = None,
        consistency_service: ClaimConsistencyService | None = None,
        official_evidence: OfficialEvidenceHeuristic | None = None,
    ) -> None:
        self.source_registry = source_registry or SourceCredibilityRegistry()
        self.claim_extractor = claim_extractor or ClusterClaimExtractor()
        self.consistency_service = consistency_service or ClaimConsistencyService()
        self.official_evidence = official_evidence or OfficialEvidenceHeuristic()

    def evaluate(self, cluster: EventCluster) -> ClusterCredibilityReport:
        """Evaluate source, claim, consistency, and official evidence signals."""
        source_summary = _source_summary(cluster, self.source_registry)
        claims = self.claim_extractor.extract(cluster)
        consistency = self.consistency_service.evaluate(claims, source_summary)
        official_status = self.official_evidence.evaluate(cluster, source_summary, claims)
        score = _score(source_summary, consistency.status, official_status)
        risk_flags = _risk_flags(source_summary, consistency.status, official_status)
        status = _credibility_status(score, source_summary, consistency.status, official_status)
        notes = [
            consistency.rationale,
            f"Official evidence status: {official_status}.",
            f"Credibility status: {status}.",
        ]
        return ClusterCredibilityReport(
            cluster_id=cluster.cluster_id,
            credibility_score=score,
            credibility_status=status,
            source_summary=source_summary,
            claims=claims,
            consistency_status=consistency.status,
            official_evidence_status=official_status,
            risk_flags=risk_flags,
            verification_notes=notes,
        )


def _source_summary(
    cluster: EventCluster,
    source_registry: SourceCredibilityRegistry,
) -> list[SourceCredibility]:
    by_source: dict[str, str | None] = {}
    for item in cluster.items:
        by_source.setdefault(item.source, item.url)
    return [source_registry.classify(source, url) for source, url in by_source.items()]


def _score(
    source_summary: list[SourceCredibility],
    consistency_status: str,
    official_status: str,
) -> float:
    non_aggregator = [source for source in source_summary if source.source_type != "aggregator"]
    high_sources = [source for source in non_aggregator if source.credibility_tier == "high"]
    score = 0.35
    score += min(len(high_sources) * 0.10, 0.30)
    score += min(max(len(non_aggregator) - 1, 0) * 0.08, 0.24)
    if official_status == "official_source_present":
        score += 0.20
    elif official_status == "official_claim_reported_by_media":
        score += 0.10
    if len(non_aggregator) <= 1:
        score -= 0.15
    if consistency_status == "analysis_only_claim":
        score -= 0.25
    if consistency_status == "unconfirmed_claim":
        score -= 0.20
    if consistency_status == "conflicting_claim":
        score -= 0.40
    if source_summary and not non_aggregator:
        score -= 0.20
    return round(min(max(score, 0.0), 0.95), 4)


def _credibility_status(
    score: float,
    source_summary: list[SourceCredibility],
    consistency_status: str,
    official_status: str,
) -> str:
    non_aggregator_count = sum(1 for source in source_summary if source.source_type != "aggregator")
    high_source_count = sum(
        1
        for source in source_summary
        if source.credibility_tier == "high" and source.source_type != "aggregator"
    )
    if consistency_status == "conflicting_claim":
        return "conflicting_claims"
    if consistency_status == "analysis_only_claim":
        return "analysis_only"
    if consistency_status == "unconfirmed_claim":
        return "unconfirmed_or_considering"
    if score >= 0.75 and (official_status != "no_official_evidence" or high_source_count):
        return "high_confidence"
    if non_aggregator_count >= 2:
        return "multi_source_supported"
    return "single_source_low_confidence"


def _risk_flags(
    source_summary: list[SourceCredibility],
    consistency_status: str,
    official_status: str,
) -> list[str]:
    flags: list[str] = []
    non_aggregator_count = sum(1 for source in source_summary if source.source_type != "aggregator")
    if source_summary and non_aggregator_count == 0:
        flags.append("aggregator_only")
    if non_aggregator_count <= 1:
        flags.append("single_source")
    if consistency_status == "analysis_only_claim":
        flags.append("analysis_only")
    if consistency_status == "unconfirmed_claim":
        flags.append("unconfirmed")
    if consistency_status == "conflicting_claim":
        flags.append("conflicting")
    if official_status == "no_official_evidence":
        flags.append("no_official_evidence")
    return flags
