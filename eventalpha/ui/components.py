"""Pure data builders for the Streamlit event console."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel, RISK_DISCLAIMER

from .formatters import (
    aggregate_rule_updates,
    aggregate_warnings,
    dedupe_event_cards,
    dedupe_review_results,
    format_event_card,
    format_lifecycle_event,
    format_review_result,
    format_rule_update,
    format_scheduler_run,
    format_tracking_policy,
)


class DashboardSummary(EventAlphaModel):
    """Compact dashboard metrics."""

    briefing_title: str = "EventAlpha Daily Briefing"
    urgent_count: int = 0
    high_count: int = 0
    normal_count: int = 0
    background_count: int = 0
    latest_auto_review_status: str = "暂无"
    latest_review_result_count: int = 0
    latest_rule_update_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    risk_disclaimer: str = RISK_DISCLAIMER
    notes: list[str] = Field(default_factory=list)


class EventConsoleData(EventAlphaModel):
    """UI-ready page data."""

    dashboard: DashboardSummary
    daily_briefing_markdown: str
    event_cards: list[dict[str, Any]] = Field(default_factory=list)
    lifecycle_events: list[dict[str, Any]] = Field(default_factory=list)
    background_events: list[dict[str, Any]] = Field(default_factory=list)
    review_results: list[dict[str, Any]] = Field(default_factory=list)
    rule_updates: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_runs: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_jobs: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_status_counts: dict[str, int] = Field(default_factory=dict)
    scheduler_job_type_counts: dict[str, int] = Field(default_factory=dict)
    scheduler_warnings: list[str] = Field(default_factory=list)
    tracking_policies: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def build_dashboard_summary(bundle: dict[str, Any]) -> DashboardSummary:
    """Build dashboard metrics from loaded local data."""
    data = bundle["collected_data"]
    urgency_counts = Counter(score.urgency_level for score in data.urgency_scores)
    latest_auto_review = next((run for run in data.recent_runs if run.job_type == "auto_review_runner"), None)
    review_result_count = _count_from_notes(latest_auto_review.notes if latest_auto_review else [], "ReviewResult count")
    rule_update_count = _count_from_notes(latest_auto_review.notes if latest_auto_review else [], "RuleUpdate count")
    report = bundle.get("latest_report")
    return DashboardSummary(
        briefing_title=_briefing_title(report),
        urgent_count=urgency_counts.get("urgent", 0),
        high_count=urgency_counts.get("high", 0),
        normal_count=urgency_counts.get("normal", 0),
        background_count=urgency_counts.get("background", 0),
        latest_auto_review_status=latest_auto_review.status if latest_auto_review else "暂无",
        latest_review_result_count=review_result_count or len(data.review_results),
        latest_rule_update_count=rule_update_count or len(data.rule_updates),
        warnings=aggregate_warnings(bundle.get("warnings", []), limit=3),
        notes=list(bundle.get("notes", [])),
    )


def build_page_data(bundle: dict[str, Any]) -> EventConsoleData:
    """Build all page data in one pure function."""
    data = bundle["collected_data"]
    urgency_by_id = {score.tracked_event_id: score for score in data.urgency_scores}
    title_by_id = {event.tracked_event_id: event.canonical_title for event in data.active_events}
    lifecycle_rows = [format_lifecycle_event(event, urgency_by_id) for event in data.active_events]
    report = bundle.get("latest_report")
    return EventConsoleData(
        dashboard=build_dashboard_summary(bundle),
        daily_briefing_markdown=report.markdown if report else "",
        event_cards=[format_event_card(row) for row in dedupe_event_cards(data.event_cards)],
        lifecycle_events=[row for row in lifecycle_rows if not row["背景分析"]],
        background_events=[row for row in lifecycle_rows if row["背景分析"]],
        review_results=[
            format_review_result(row)
            for row in dedupe_review_results(data.review_results, recent_runs=data.recent_runs)
        ],
        rule_updates=[format_rule_update(row) for row in aggregate_rule_updates(data.rule_updates)],
        scheduler_runs=[format_scheduler_run(run) for run in data.recent_runs],
        scheduler_jobs=[job.model_dump(mode="json") for job in data.scheduler_jobs],
        scheduler_status_counts=dict(Counter(run.status for run in data.recent_runs)),
        scheduler_job_type_counts=dict(Counter(run.job_type for run in data.recent_runs)),
        scheduler_warnings=aggregate_warnings(data.warnings, limit=3),
        tracking_policies=[
            format_tracking_policy(policy, title_by_id)
            for policy in data.tracking_policies
        ],
        notes=list(bundle.get("notes", [])),
    )


def _briefing_title(report: Any) -> str:
    if report and report.json_payload:
        title = report.json_payload.get("title")
        if title:
            return str(title)
    if report and report.briefing_date:
        return f"EventAlpha Daily Briefing - {report.briefing_date.isoformat()}"
    return "EventAlpha Daily Briefing"


def _count_from_notes(notes: list[str], label: str) -> int:
    prefix = f"{label}:"
    for note in notes:
        if note.startswith(prefix):
            try:
                return int(note.removeprefix(prefix).strip().rstrip("."))
            except ValueError:
                return 0
    return 0
