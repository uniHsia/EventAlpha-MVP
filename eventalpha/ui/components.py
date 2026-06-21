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
    format_credibility_label,
    format_event_card,
    format_lifecycle_event,
    format_lifecycle_stage,
    format_priority_label,
    format_review_result,
    format_rule_update,
    format_scheduler_run,
    format_tracking_policy,
    format_warning_friendly,
)


class MetricCard(EventAlphaModel):
    """One dashboard metric with a human explanation."""

    label: str
    value: str | int | float
    help_text: str


class DashboardSummary(EventAlphaModel):
    """Presentation-ready dashboard metrics and highlights."""

    briefing_title: str = "EventAlpha Daily Briefing"
    metric_cards: list[MetricCard] = Field(default_factory=list)
    urgent_count: int = 0
    high_count: int = 0
    normal_count: int = 0
    background_count: int = 0
    latest_auto_review_status: str = "暂无"
    latest_review_result_count: int = 0
    latest_rule_update_count: int = 0
    top_events: list[dict[str, Any]] = Field(default_factory=list)
    recent_reviews: list[dict[str, Any]] = Field(default_factory=list)
    recent_rule_updates: list[dict[str, Any]] = Field(default_factory=list)
    friendly_warnings: list[str] = Field(default_factory=list)
    raw_warnings: list[str] = Field(default_factory=list)
    system_status_notes: list[str] = Field(default_factory=list)
    risk_disclaimer: str = RISK_DISCLAIMER
    notes: list[str] = Field(default_factory=list)


class EventConsoleData(EventAlphaModel):
    """UI-ready page data."""

    dashboard: DashboardSummary
    daily_briefing_markdown: str
    daily_briefing_json: dict[str, Any] = Field(default_factory=dict)
    event_cards: list[dict[str, Any]] = Field(default_factory=list)
    event_card_duplicate_total: int = 0
    lifecycle_events: list[dict[str, Any]] = Field(default_factory=list)
    background_events: list[dict[str, Any]] = Field(default_factory=list)
    review_results: list[dict[str, Any]] = Field(default_factory=list)
    review_summary: dict[str, Any] = Field(default_factory=dict)
    rule_updates: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_runs: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_jobs: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_status_counts: dict[str, int] = Field(default_factory=dict)
    scheduler_job_type_counts: dict[str, int] = Field(default_factory=dict)
    scheduler_warnings: list[str] = Field(default_factory=list)
    friendly_scheduler_warnings: list[str] = Field(default_factory=list)
    tracking_policies: list[dict[str, Any]] = Field(default_factory=list)
    raw_debug: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


def build_dashboard_summary(bundle: dict[str, Any]) -> DashboardSummary:
    """Build dashboard metrics from loaded local data."""
    data = bundle["collected_data"]
    urgency_counts = Counter(score.urgency_level for score in data.urgency_scores)
    latest_auto_review = next((run for run in data.recent_runs if run.job_type == "auto_review_runner"), None)
    review_result_count = _count_from_notes(latest_auto_review.notes if latest_auto_review else [], "ReviewResult count")
    rule_update_count = _count_from_notes(latest_auto_review.notes if latest_auto_review else [], "RuleUpdate count")
    review_result_count = review_result_count or len(data.review_results)
    rule_update_count = rule_update_count or len(data.rule_updates)
    report = bundle.get("latest_report")

    raw_warnings = aggregate_warnings(bundle.get("warnings", []), limit=3)
    top_events = bundle.get("top_events") or _build_top_events(data)
    recent_reviews = bundle.get("recent_reviews") or _build_recent_reviews(data)
    recent_rule_updates = bundle.get("recent_rule_updates") or _build_recent_rule_updates(data)
    friendly_warnings = bundle.get("friendly_warnings") or format_warning_friendly(raw_warnings)

    status_notes = [
        _latest_run_note("scheduler_status", data.recent_runs),
        _latest_run_note("auto_review_runner", data.recent_runs),
        "当前页面展示本地 demo/mock 数据与本地持久化结果，不代表真实市场结论。",
    ]

    return DashboardSummary(
        briefing_title=_briefing_title(report),
        urgent_count=urgency_counts.get("urgent", 0),
        high_count=urgency_counts.get("high", 0),
        normal_count=urgency_counts.get("normal", 0),
        background_count=urgency_counts.get("background", 0),
        latest_auto_review_status=latest_auto_review.status if latest_auto_review else "暂无",
        latest_review_result_count=review_result_count,
        latest_rule_update_count=rule_update_count,
        metric_cards=[
            MetricCard(label="紧急事件", value=urgency_counts.get("urgent", 0), help_text="需要高频追踪的突发事件"),
            MetricCard(label="高优先级", value=urgency_counts.get("high", 0), help_text="需要增强跟踪的事件"),
            MetricCard(label="普通跟踪", value=urgency_counts.get("normal", 0), help_text="按常规频率观察的事件"),
            MetricCard(label="背景观察", value=urgency_counts.get("background", 0), help_text="分析类、评论类或低优先级事件"),
            MetricCard(label="自动复盘状态", value=latest_auto_review.status if latest_auto_review else "暂无", help_text="最近一次到期复盘任务是否成功"),
            MetricCard(label="复盘结果数", value=review_result_count, help_text="最近一次复盘生成的资产级 ReviewResult 数量"),
            MetricCard(label="规则更新数", value=rule_update_count, help_text="复盘后触发的规则调整数量"),
        ],
        top_events=top_events,
        recent_reviews=recent_reviews,
        recent_rule_updates=recent_rule_updates,
        friendly_warnings=friendly_warnings,
        raw_warnings=raw_warnings,
        system_status_notes=[note for note in status_notes if note],
        notes=list(bundle.get("notes", [])),
    )


def build_page_data(bundle: dict[str, Any]) -> EventConsoleData:
    """Build all page data in one pure function."""
    data = bundle["collected_data"]
    urgency_by_id = {score.tracked_event_id: score for score in data.urgency_scores}
    title_by_id = {event.tracked_event_id: event.canonical_title for event in data.active_events}
    lifecycle_rows = [format_lifecycle_event(event, urgency_by_id) for event in data.active_events]
    deduped_cards = dedupe_event_cards(data.event_cards)
    event_card_duplicate_total = sum(max(int(row.get("duplicate_count") or 1) - 1, 0) for row in deduped_cards)
    review_rows = [
        format_review_result(row)
        for row in dedupe_review_results(data.review_results, recent_runs=data.recent_runs)
    ]
    rule_rows = [format_rule_update(row) for row in aggregate_rule_updates(data.rule_updates)]
    report = bundle.get("latest_report")
    warnings = aggregate_warnings(data.warnings, limit=3)
    return EventConsoleData(
        dashboard=build_dashboard_summary(bundle),
        daily_briefing_markdown=report.markdown if report else "",
        daily_briefing_json=report.json_payload if report else {},
        event_cards=[format_event_card(row) for row in deduped_cards],
        event_card_duplicate_total=event_card_duplicate_total,
        lifecycle_events=[row for row in lifecycle_rows if not row["背景分析"]],
        background_events=[row for row in lifecycle_rows if row["背景分析"]],
        review_results=review_rows,
        review_summary=_build_review_summary(review_rows),
        rule_updates=rule_rows,
        scheduler_runs=[format_scheduler_run(run) for run in data.recent_runs],
        scheduler_jobs=[job.model_dump(mode="json") for job in data.scheduler_jobs],
        scheduler_status_counts=dict(Counter(run.status for run in data.recent_runs)),
        scheduler_job_type_counts=dict(Counter(run.job_type for run in data.recent_runs)),
        scheduler_warnings=warnings,
        friendly_scheduler_warnings=format_warning_friendly(warnings),
        tracking_policies=[
            format_tracking_policy(policy, title_by_id)
            for policy in data.tracking_policies
        ],
        raw_debug={
            "scheduler_status_counts": dict(Counter(run.status for run in data.recent_runs)),
            "scheduler_job_type_counts": dict(Counter(run.job_type for run in data.recent_runs)),
            "notes": list(bundle.get("notes", [])),
            "raw_warnings": warnings,
        },
        notes=list(bundle.get("notes", [])),
    )


def _build_top_events(data: Any, *, limit: int = 3) -> list[dict[str, Any]]:
    scores_by_id = {score.tracked_event_id: score for score in data.urgency_scores}
    candidates = []
    for event in data.active_events:
        score = scores_by_id.get(event.tracked_event_id)
        if not score or score.urgency_level in {"background", "ignore"}:
            continue
        if event.lifecycle_stage == "analysis_only":
            continue
        row = format_lifecycle_event(event, scores_by_id)
        row.update(
            {
                "为什么重要": "; ".join(score.reasons[:2]) or "事件仍在发展，值得继续观察。",
                "验证指标": score.reasons[:2],
            }
        )
        candidates.append((score.urgency_score, row))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in candidates[:limit]]


def _build_recent_reviews(data: Any, *, limit: int = 5) -> list[dict[str, Any]]:
    return [
        format_review_result(row)
        for row in dedupe_review_results(data.review_results, recent_runs=data.recent_runs)[:limit]
    ]


def _build_recent_rule_updates(data: Any, *, limit: int = 3) -> list[dict[str, Any]]:
    return [format_rule_update(row) for row in aggregate_rule_updates(data.rule_updates)[:limit]]


def _build_review_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    validity_counts = Counter(row.get("因果有效性") or "unknown" for row in rows)
    excess_values = []
    for row in rows:
        value = row.get("超额收益原值")
        if value is None:
            continue
        try:
            excess_values.append(float(value))
        except (TypeError, ValueError):
            continue
    avg_excess = sum(excess_values) / len(excess_values) if excess_values else None
    return {
        "复盘结果数": len(rows),
        "valid": validity_counts.get("valid", 0),
        "invalid": validity_counts.get("invalid", 0),
        "unknown": validity_counts.get("unknown", 0),
        "平均超额收益": avg_excess,
        "提示": "当前为 mock/demo 复盘数据，仅用于演示闭环。",
    }


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


def _latest_run_note(job_type: str, runs: list[Any]) -> str:
    run = next((item for item in runs if item.job_type == job_type), None)
    if not run:
        return f"最近 {job_type}：暂无运行记录。"
    return f"最近 {job_type}：{run.status}，开始时间 {run.started_at}。"
