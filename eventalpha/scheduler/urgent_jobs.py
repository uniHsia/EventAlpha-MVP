"""Urgent-mode scheduler job and decision schema."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from eventalpha.news import DEFAULT_LIFECYCLE_STORE_PATH, EventLifecycleStore
from eventalpha.schemas.base import EventAlphaModel, utc_now

from .priority_ranker import EventPriorityRanker
from .schemas import SchedulerJobConfig, SchedulerRunRecord
from .state_store import SchedulerStateStore
from .tracking_policy import TrackingPolicy, TrackingPolicyService
from .urgency import EventUrgencyScore


class UrgentModeDecision(EventAlphaModel):
    """Urgent-mode decision for active lifecycle events."""

    urgent_events: list[EventUrgencyScore] = Field(default_factory=list)
    high_priority_events: list[EventUrgencyScore] = Field(default_factory=list)
    background_events: list[EventUrgencyScore] = Field(default_factory=list)
    tracking_policies: list[TrackingPolicy] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def run_urgent_event_scan(
    config: SchedulerJobConfig,
    store: SchedulerStateStore,
    *,
    lifecycle_store_path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH,
    ranker: EventPriorityRanker | None = None,
    policy_service: TrackingPolicyService | None = None,
) -> SchedulerRunRecord:
    """Rank active events and optionally save urgent-mode tracking policies."""
    record = SchedulerRunRecord(
        job_id=config.job_id,
        job_type=config.job_type,
        started_at=utc_now(),
        status="started",
    )
    try:
        lifecycle_store = EventLifecycleStore(lifecycle_store_path).load()
        active_events = lifecycle_store.list_active_events()
        scores = (ranker or EventPriorityRanker()).rank(active_events)
        policies = (policy_service or TrackingPolicyService()).build_policies(scores)
        decision = build_urgent_mode_decision(scores=scores, policies=policies, limit=config.limit)
        notes = list(decision.notes)
        if config.dry_run:
            notes.append("Dry-run: tracking policies were not saved.")
            record = record.model_copy(
                update={
                    "candidate_items": len(active_events),
                    "notes": notes,
                }
            ).finish("dry_run")
        else:
            store.save_tracking_policies(policies)
            notes.append("Tracking policies saved to scheduler state.")
            record = record.model_copy(
                update={
                    "candidate_items": len(active_events),
                    "lifecycle_updates": len(policies),
                    "notes": notes,
                }
            ).finish("success")
    except Exception as exc:  # pragma: no cover - defensive job boundary
        record = record.finish("failed", errors=record.errors + [str(exc)])
    store.append_run(record)
    return record


def build_urgent_mode_decision(
    *,
    scores: list[EventUrgencyScore],
    policies: list[TrackingPolicy],
    limit: int = 10,
) -> UrgentModeDecision:
    """Build a compact decision object from urgency scores and policies."""
    urgent_events = [score for score in scores if score.urgency_level == "urgent"]
    high_priority_events = [score for score in scores if score.urgency_level == "high"]
    background_events = [
        score for score in scores if score.urgency_level in {"background", "ignore"}
    ]
    normal_count = sum(1 for score in scores if score.urgency_level == "normal")
    notes = [
        f"Urgent events: {len(urgent_events)}.",
        f"High priority events: {len(high_priority_events)}.",
        f"Normal events: {normal_count}.",
        f"Background or paused events: {len(background_events)}.",
    ]
    for score in urgent_events[:limit]:
        reason = score.reasons[0] if score.reasons else "no primary reason"
        notes.append(f"Top urgent: {score.title} ({score.urgency_score:.1f}) - {reason}.")
    for score in high_priority_events[: max(0, limit - len(urgent_events))]:
        reason = score.reasons[0] if score.reasons else "no primary reason"
        notes.append(f"Top high priority: {score.title} ({score.urgency_score:.1f}) - {reason}.")
    return UrgentModeDecision(
        urgent_events=urgent_events,
        high_priority_events=high_priority_events,
        background_events=background_events,
        tracking_policies=policies,
        notes=notes,
    )
