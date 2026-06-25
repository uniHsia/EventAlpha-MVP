"""Unified credibility normalization for cluster-origin event candidates."""

from __future__ import annotations

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel

from .schemas import ClusterCredibilityReport, EventCluster


class NormalizedClusterCredibility(EventAlphaModel):
    """Single source of truth for cluster-derived credibility fields."""

    verification_status: str
    credibility_score: float
    official_confirmation: str
    independent_confirmation: bool = False
    reason_codes: list[str] = Field(default_factory=list)


def normalize_cluster_credibility(
    cluster: EventCluster,
    credibility_report: ClusterCredibilityReport | None = None,
) -> NormalizedClusterCredibility:
    """Map cluster/report signals into one conservative user-facing credibility truth."""
    official_confirmation = (
        getattr(credibility_report, "official_evidence_status", None)
        or "no_official_evidence"
    )
    consistency_status = getattr(credibility_report, "consistency_status", None) or ""
    risk_flags = set(getattr(credibility_report, "risk_flags", []) or [])
    reason_codes: list[str] = [f"cluster_type:{cluster.cluster_type}"]
    if official_confirmation:
        reason_codes.append(f"official:{official_confirmation}")
    if consistency_status:
        reason_codes.append(f"consistency:{consistency_status}")
    reason_codes.extend(sorted(risk_flags))

    if consistency_status == "conflicting_claim" or "conflicting" in risk_flags:
        return NormalizedClusterCredibility(
            verification_status="conflict_detected",
            credibility_score=0.45,
            official_confirmation=official_confirmation,
            independent_confirmation=False,
            reason_codes=reason_codes,
        )

    if cluster.cluster_type in {"same_source_topic_cluster", "analysis_digest"}:
        return NormalizedClusterCredibility(
            verification_status="analysis_only",
            credibility_score=0.35,
            official_confirmation=official_confirmation,
            independent_confirmation=False,
            reason_codes=reason_codes,
        )

    if cluster.unique_source_count <= 1:
        if official_confirmation == "official_source_present":
            return NormalizedClusterCredibility(
                verification_status="official_single_source",
                credibility_score=0.55,
                official_confirmation=official_confirmation,
                independent_confirmation=False,
                reason_codes=reason_codes,
            )
        return NormalizedClusterCredibility(
            verification_status="single_source_low_confidence",
            credibility_score=0.4,
            official_confirmation=official_confirmation,
            independent_confirmation=False,
            reason_codes=reason_codes,
        )

    if official_confirmation == "official_source_present":
        return NormalizedClusterCredibility(
            verification_status="confirmed",
            credibility_score=0.8,
            official_confirmation=official_confirmation,
            independent_confirmation=True,
            reason_codes=reason_codes,
        )

    return NormalizedClusterCredibility(
        verification_status="multi_source_observed",
        credibility_score=0.68,
        official_confirmation=official_confirmation,
        independent_confirmation=cluster.independent_confirmation or cluster.unique_source_count >= 2,
        reason_codes=reason_codes,
    )
