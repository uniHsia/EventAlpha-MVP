"""Initial multi-source support summary for event clusters."""

from __future__ import annotations

from .schemas import EventCluster


ANALYSIS_SOURCE_HINTS = (
    "analysis",
    "blog",
    "brookings",
    "foundation",
    "policy press",
    "think tank",
    "opinion",
)
UNCONFIRMED_HINTS = (
    "rumor",
    "reportedly",
    "considering",
    "weighs",
    "mulls",
    "据称",
    "考虑",
    "拟",
    "传闻",
)


class ClusterVerificationService:
    """Assign preliminary source-support status to an EventCluster."""

    def verify(self, cluster: EventCluster) -> EventCluster:
        """Return a copied cluster with verification fields updated."""
        status = _support_status(cluster)
        confidence = _confidence_for_status(cluster, status)
        return cluster.model_copy(
            update={
                "verification_status": status,
                "confidence": confidence,
                "debug_reasons": _append_reason(
                    cluster.debug_reasons,
                    f"cluster verification: {status}",
                ),
            }
        )


def _support_status(cluster: EventCluster) -> str:
    title_text = f"{cluster.canonical_title} {cluster.canonical_summary or ''}".casefold()
    if any(hint in title_text for hint in UNCONFIRMED_HINTS):
        return "unconfirmed_or_considering"
    if _analysis_only(cluster):
        return "analysis_only"
    if cluster.source_count >= 3 and cluster.mainstream_source_count >= 2:
        return "multi_source_supported"
    if cluster.source_count >= 2:
        return "multi_source_observed"
    return "single_source"


def _analysis_only(cluster: EventCluster) -> bool:
    if not cluster.items:
        return False
    analysis_like = 0
    for item in cluster.items:
        text = f"{item.source} {item.source_type} {item.title}".casefold()
        if item.source_type == "research_report" or any(hint in text for hint in ANALYSIS_SOURCE_HINTS):
            analysis_like += 1
    return analysis_like == len(cluster.items)


def _confidence_for_status(cluster: EventCluster, status: str) -> float:
    base = {
        "multi_source_supported": 0.78,
        "multi_source_observed": 0.62,
        "single_source": 0.38,
        "analysis_only": 0.32,
        "unconfirmed_or_considering": 0.30,
    }[status]
    if status.startswith("multi_source"):
        base += min(max(cluster.source_count - 2, 0) * 0.03, 0.09)
    return round(min(base, 0.85), 4)


def _append_reason(existing: list[str], reason: str) -> list[str]:
    if reason in existing:
        return existing
    return [*existing, reason]
