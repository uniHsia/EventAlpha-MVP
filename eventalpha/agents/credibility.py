"""Rule-based mock credibility agent."""

from __future__ import annotations

from eventalpha.schemas import EventVerification, RawNews, StructuredEvent


MAINSTREAM_MEDIA = {
    "reuters",
    "bloomberg",
    "wsj",
    "wall street journal",
    "ft",
    "financial times",
    "ap",
    "associated press",
    "xinhua",
    "新华社",
    "央视新闻",
}
OFFICIAL_SOURCES = {
    "white house",
    "u.s. department of commerce",
    "us department of commerce",
    "federal reserve",
    "the fed",
    "白宫",
    "美国商务部",
    "美联储",
    "中国央行",
    "中国人民银行",
    "证监会",
    "上交所",
    "深交所",
    "港交所",
    "交易所",
    "公司公告原文",
}
OFFICIAL_CLAIM_KEYWORDS = ["公告", "宣布", "官方", "声明", "发布", "商务部", "美联储"]


def _classify_source(raw_news: RawNews) -> str:
    """Classify source identity without relying on claims inside article text."""
    source = raw_news.source.lower()
    source_original = raw_news.source

    if raw_news.source_type == "official" or any(
        item in source or item in source_original for item in OFFICIAL_SOURCES
    ):
        return "official_source"
    if raw_news.source_type == "social_media":
        return "social_media"
    if raw_news.source_type == "mainstream_media":
        return "mainstream_media"
    if any(item in source or item in source_original for item in MAINSTREAM_MEDIA):
        return "recognized_media"
    return "unknown_source"


def verify_event(raw_news: RawNews, event: StructuredEvent) -> EventVerification:
    """Assign a deterministic credibility score from source metadata."""
    cluster_status = raw_news.metadata.get("verification_status")
    cluster_score = raw_news.metadata.get("cluster_credibility_score") or raw_news.metadata.get("confidence")
    if raw_news.metadata.get("cluster_id") and cluster_status and cluster_score:
        try:
            parsed_score = max(0.0, min(1.0, round(float(cluster_score), 2)))
        except (TypeError, ValueError):
            parsed_score = 0.5
        evidence = [
            {
                "source": raw_news.source,
                "type": "cluster_origin",
            }
        ]
        official_confirmation = raw_news.metadata.get("official_confirmation") or raw_news.metadata.get("official_evidence_status")
        if official_confirmation and official_confirmation != "no_official_evidence":
            evidence.append({"source": raw_news.source, "type": official_confirmation})
        risk_flags = []
        raw_risk_flags = raw_news.metadata.get("credibility_risk_flags") or ""
        if raw_risk_flags:
            risk_flags = [flag for flag in raw_risk_flags.split(",") if flag]
        return EventVerification(
            event_id=event.event_id,
            credibility_score=parsed_score,
            verification_status=cluster_status,  # type: ignore[arg-type]
            source_classification=_classify_source(raw_news),  # type: ignore[arg-type]
            content_contains_official_claim=official_confirmation in {"official_source_present", "official_claim_reported_by_media"},
            evidence=evidence,
            risk_flags=risk_flags,
        )

    text = f"{raw_news.title} {raw_news.raw_text}"
    score = 0.45
    evidence: list[dict[str, str]] = []
    risk_flags: list[str] = []
    source_classification = _classify_source(raw_news)
    content_contains_official_claim = any(k in text for k in OFFICIAL_CLAIM_KEYWORDS)

    if source_classification == "official_source":
        score += 0.35
        evidence.append({"source": raw_news.source, "type": "official_source"})
    elif source_classification == "mainstream_media":
        score += 0.25
        evidence.append({"source": raw_news.source, "type": "mainstream_media"})
    elif source_classification == "recognized_media":
        score += 0.20
        evidence.append({"source": raw_news.source, "type": "recognized_media"})
    elif source_classification == "social_media":
        score -= 0.10
        risk_flags.append("来源为社交媒体，需要交叉验证")

    if content_contains_official_claim:
        score += 0.05
        evidence.append({"source": raw_news.source, "type": "content_contains_official_claim"})

    if any(k in text for k in ["网传", "据传", "未经证实"]):
        score -= 0.25
        risk_flags.append("存在传闻或未经证实表述")

    if any(k in text for k in ["考虑", "可能", "计划"]):
        score -= 0.05
        risk_flags.append("政策细节可能仍有不确定性")

    score = max(0.0, min(1.0, round(score, 2)))
    if score >= 0.85:
        status = "confirmed"
    elif score >= 0.70:
        status = "high_confidence"
    elif score >= 0.55:
        status = "needs_confirmation"
    elif score >= 0.40:
        status = "low_confidence"
    else:
        status = "rumor"

    return EventVerification(
        event_id=event.event_id,
        credibility_score=score,
        verification_status=status,
        source_classification=source_classification,  # type: ignore[arg-type]
        content_contains_official_claim=content_contains_official_claim,
        evidence=evidence,
        risk_flags=risk_flags,
    )
