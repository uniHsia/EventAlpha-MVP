"""Priority ranking for active lifecycle events."""

from __future__ import annotations

from datetime import timedelta

from eventalpha.news import TrackedEvent
from eventalpha.schemas.base import utc_now

from .urgency import EventUrgencyScore, UrgencyLevel, urgency_level_for_score


HIGH_IMPACT_TERMS = (
    "conflict",
    "war",
    "attack",
    "rate",
    "tariff",
    "export control",
    "ai chip",
    "chip export",
    "earthquake",
    "geopolitical",
    "geopolitical_conflict",
    "rate_policy",
    "trade_tariff",
    "ai_export_control",
    "earthquake_supply_chain",
)
COMMENTARY_TERMS = ("think tank", "commentary", "opinion", "analysis only", "research")
HISTORICAL_VALIDATION_TERMS = ("historically_weakened", "requires_verification")


class EventPriorityRanker:
    """Rank tracked lifecycle events by urgency."""

    def rank(self, tracked_events: list[TrackedEvent]) -> list[EventUrgencyScore]:
        """Return urgency scores sorted highest first."""
        scores = [self.score(event) for event in tracked_events]
        return sorted(
            scores,
            key=lambda item: (item.urgency_score, _level_rank(item.urgency_level), item.title),
            reverse=True,
        )

    def score(self, event: TrackedEvent) -> EventUrgencyScore:
        """Score one tracked lifecycle event."""
        reasons: list[str] = []
        penalties: list[str] = []
        if not event.is_active or event.lifecycle_stage in {"closed", "resolved"}:
            return EventUrgencyScore(
                tracked_event_id=event.tracked_event_id,
                title=event.canonical_title,
                urgency_score=0,
                urgency_level="ignore",
                penalties=["inactive or closed event"],
            )

        score = 20.0
        stage = (event.lifecycle_stage or "").casefold()
        credibility = (event.credibility_status or "").casefold()
        official = (event.official_evidence_status or "").casefold()
        text = _event_text(event)

        if stage in {"new", "developing"}:
            score += 15
            reasons.append(f"lifecycle_stage={event.lifecycle_stage}")
        elif stage == "confirmed":
            score += 10
            reasons.append("confirmed lifecycle stage")

        if credibility == "high_confidence":
            score += 25
            reasons.append("high confidence credibility")
        elif credibility == "multi_source_supported":
            score += 20
            reasons.append("multi-source supported credibility")

        if official == "official_source_present":
            score += 15
            reasons.append("official source present")

        if event.source_count >= 4:
            score += 15
            reasons.append("source_count>=4")
        elif event.source_count >= 2:
            score += 10
            reasons.append("source_count>=2")

        if _contains_any(text, HIGH_IMPACT_TERMS):
            score += 15
            reasons.append("high-impact event type or keywords")

        if _contains_any(text, ("event_level=a", "event_level a", "trigger_alert")):
            score += 10
            reasons.append("alert metadata present")

        if _contains_any(text, HISTORICAL_VALIDATION_TERMS):
            score += 10
            reasons.append("history validation requires attention")

        age = utc_now() - event.last_seen_at
        if age <= timedelta(hours=24):
            score += 10
            reasons.append("updated within 24h")
        elif age > timedelta(days=7):
            score -= 15
            penalties.append("older than 7 days")

        if stage == "analysis_only":
            score -= 35
            penalties.append("analysis_only lifecycle stage")
        if credibility == "single_source_low_confidence":
            score -= 20
            penalties.append("single source low confidence")
        if stage == "unconfirmed_or_considering":
            score -= 15
            penalties.append("unconfirmed or considering")
        if stage == "stale":
            score -= 30
            penalties.append("stale lifecycle stage")
        if _contains_any(" ".join(event.sources), COMMENTARY_TERMS) or _contains_any(text, COMMENTARY_TERMS):
            score -= 15
            penalties.append("commentary or research-only source")

        level = _apply_caps(
            urgency_level_for_score(score),
            stage=stage,
            credibility=credibility,
            event=event,
            penalties=penalties,
        )
        return EventUrgencyScore(
            tracked_event_id=event.tracked_event_id,
            title=event.canonical_title,
            urgency_score=score,
            urgency_level=level,
            reasons=reasons,
            penalties=penalties,
        )


def _event_text(event: TrackedEvent) -> str:
    timeline_text = " ".join(
        " ".join(entry.notes) + f" {entry.title or ''} {entry.summary or ''}"
        for entry in event.timeline
    )
    return " ".join(
        [
            event.canonical_title,
            event.current_summary or "",
            event.lifecycle_stage or "",
            event.credibility_status or "",
            event.official_evidence_status or "",
            " ".join(event.latest_claims),
            " ".join(event.dominant_keywords),
            " ".join(event.sources),
            timeline_text,
        ]
    ).casefold()


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    text = value.casefold()
    return any(term.casefold() in text for term in terms)


def _apply_caps(
    level: UrgencyLevel,
    *,
    stage: str,
    credibility: str,
    event: TrackedEvent,
    penalties: list[str],
) -> UrgencyLevel:
    if not event.is_active or stage in {"closed", "resolved"}:
        return "ignore"
    if stage == "analysis_only":
        return "background"
    if stage == "unconfirmed_or_considering" or credibility == "unconfirmed_or_considering":
        return _min_level(level, "high")
    if stage == "stale":
        return _min_level(level, "background")
    return level


def _min_level(level: UrgencyLevel, cap: UrgencyLevel) -> UrgencyLevel:
    order = ["ignore", "background", "normal", "high", "urgent"]
    return order[min(order.index(level), order.index(cap))]  # type: ignore[return-value]


def _level_rank(level: str) -> int:
    return {
        "ignore": 0,
        "background": 1,
        "normal": 2,
        "high": 3,
        "urgent": 4,
    }.get(level, 0)
