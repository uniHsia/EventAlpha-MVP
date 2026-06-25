"""Convert event clusters to EventAlpha RawNews."""

from __future__ import annotations

from eventalpha.schemas import RawNews

from .schemas import ClusterCredibilityReport, EventCluster


def event_cluster_to_raw_news(
    cluster: EventCluster,
    credibility_report: ClusterCredibilityReport | None = None,
) -> RawNews:
    """Convert an EventCluster to RawNews without changing the RawNews schema."""
    urls = [item.url for item in cluster.items if item.url]
    item_ids = [item.news_id for item in cluster.items]
    source_names = _unique(cluster.sources)[:5]
    summaries = [
        item.raw_text or item.summary
        for item in cluster.items
        if item.raw_text or item.summary
    ]
    raw_text = cluster.canonical_summary or "\n".join(str(item) for item in summaries[:3]) or cluster.canonical_title
    metadata = {
        "cluster_id": cluster.cluster_id,
        "source_count": str(cluster.source_count),
        "item_count": str(cluster.item_count or len(cluster.items)),
        "unique_source_count": str(cluster.unique_source_count or cluster.source_count),
        "cluster_type": cluster.cluster_type,
        "independent_confirmation": "true" if cluster.independent_confirmation else "false",
        "verification_status": cluster.verification_status,
        "confidence": f"{cluster.confidence:.4f}",
        "urls": "|".join(urls),
        "item_ids": "|".join(item_ids),
        "dominant_keywords": ",".join(cluster.dominant_keywords),
    }
    if credibility_report:
        metadata.update(
            {
                "cluster_credibility_score": f"{credibility_report.credibility_score:.4f}",
                "cluster_credibility_status": credibility_report.credibility_status,
                "claim_consistency_status": credibility_report.consistency_status,
                "official_evidence_status": credibility_report.official_evidence_status,
                "credibility_risk_flags": ",".join(credibility_report.risk_flags),
                "verification_notes": " | ".join(credibility_report.verification_notes),
                "official_confirmation": credibility_report.official_evidence_status,
            }
        )

    return RawNews(
        raw_id=cluster.cluster_id,
        title=cluster.canonical_title,
        source=", ".join(source_names) or "news_cluster",
        source_type=_cluster_source_type(cluster),
        publish_time=cluster.last_seen_at or cluster.first_seen_at,
        url=urls[0] if urls else None,
        language=_cluster_language(cluster),
        raw_text=raw_text,
        metadata=metadata,
    )


def _cluster_source_type(cluster: EventCluster) -> str:
    if cluster.cluster_type in {"same_source_topic_cluster", "analysis_digest"} or cluster.verification_status == "analysis_only":
        return "research_report"
    if cluster.mainstream_source_count:
        return "mainstream_media"
    return "unknown"


def _cluster_language(cluster: EventCluster) -> str:
    for item in cluster.items:
        if item.language:
            return item.language
    return "unknown"


def _unique(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
