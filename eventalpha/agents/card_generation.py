"""Mock event card generation agent."""

from __future__ import annotations

from typing import Any

from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    EventCard,
    EventVerification,
    ImpactScore,
    MarketMapping,
    RawNews,
    StructuredEvent,
)
from eventalpha.schemas.base import utc_now
from eventalpha.services import CritiqueCompressionService


_critique_service = CritiqueCompressionService()


def _impact_text(asset_name: str, direction: str, final_confidence: float) -> str:
    confidence_text = f"最终置信度={final_confidence:.2f}"
    if direction == "up":
        return f"{asset_name}: 可能受益或受到市场关注（{confidence_text}）"
    if direction == "down":
        return f"{asset_name}: 可能承压（{confidence_text}）"
    return f"{asset_name}: 需要继续观察（{confidence_text}）"


def generate_event_card(
    raw_news: RawNews,
    event: StructuredEvent,
    verification: EventVerification,
    score: ImpactScore,
    chain: CausalChain,
    anti_spurious: AntiSpuriousCheck,
    mapping: MarketMapping,
    history_validation_summary: Any | None = None,
) -> EventCard:
    """Create a user-facing research card from structured outputs."""
    possible_impacts = [
        _impact_text(
            asset.asset_name,
            asset.direction,
            round(asset.confidence * anti_spurious.adjusted_confidence, 4),
        )
        for asset in mapping.mapped_assets
    ]
    risk_factors = _critique_service.compact_event_card_risk_factors(
        risk_flags=list(verification.risk_flags) + _history_risk_notes(history_validation_summary),
        anti_spurious_issues=list(anti_spurious.issues) + _history_risk_signals(history_validation_summary),
        limit=6,
    )
    if not risk_factors:
        risk_factors = ["市场可能已经提前反映部分事件信息"]

    verification_indicators = _critique_service.compact_event_card_verification_indicators(
        watch_indicators=list(mapping.watch_indicators),
        required_verifications=list(anti_spurious.required_verifications)
        + _history_verification_indicators(history_validation_summary),
        limit=8,
    )

    industries = "、".join(event.affected_industries[:3]) or "相关市场"
    return EventCard(
        event_id=event.event_id,
        event_title=event.event_title,
        event_level=score.event_level,
        credibility_score=verification.credibility_score,
        one_sentence=(
            f"{event.event_title}可能影响{industries}，"
            "仍需结合后续市场数据验证。"
        ),
        what_happened=event.summary,
        sources=[raw_news.source],
        causal_chain_summary=[step.description for step in chain.logic],
        possible_impacts=possible_impacts,
        risk_factors=risk_factors,
        verification_indicators=verification_indicators,
        source_evidence=list(verification.evidence),
        verification_status=verification.verification_status,
        official_confirmation=(
            "official_source_present"
            if verification.source_classification == "official_source"
            else "official_claim_reported_by_media"
            if verification.content_contains_official_claim
            else "no_official_evidence"
        ),
        staleness_flag=_staleness_flag(raw_news.publish_time),
        history_validation_summary=_summary_payload(history_validation_summary),
    )


def _history_risk_notes(summary: Any | None) -> list[str]:
    if summary is None:
        return []
    return list(getattr(summary, "risk_notes", []))


def _history_risk_signals(summary: Any | None) -> list[str]:
    if summary is None:
        return []
    items = [
        signal
        for signal in getattr(summary, "top_signals", [])
        if _is_history_risk_signal(signal)
    ]
    if getattr(summary, "overall_validation", None) == "historically_weakened":
        items.append("Historical validation weakened the current causal chain.")
    return items


def _history_verification_indicators(summary: Any | None) -> list[str]:
    if summary is None:
        return []
    items = list(getattr(summary, "required_verifications", []))
    items.extend(
        signal
        for signal in getattr(summary, "top_signals", [])
        if "requires_verification" in str(signal)
    )
    items.extend(list(getattr(summary, "asset_notes", [])))
    return items


def _is_history_risk_signal(value: str) -> bool:
    text = str(value)
    return any(
        marker in text
        for marker in (
            "priced_in_risk",
            "second_order_warning",
            "historically_weakened",
            "weakens_chain",
            "demo_only",
        )
    )


def _summary_payload(summary: Any | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    if hasattr(summary, "model_dump"):
        return summary.model_dump(mode="json")
    if isinstance(summary, dict):
        return dict(summary)
    return None


def _staleness_flag(publish_time: Any) -> str:
    if not hasattr(publish_time, "__sub__"):
        return "unknown"
    try:
        age = utc_now() - publish_time
    except TypeError:
        return "unknown"
    if age.days >= 14:
        return "stale"
    if age.days >= 3:
        return "aging"
    return "fresh"
