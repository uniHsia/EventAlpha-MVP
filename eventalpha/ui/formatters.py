"""Formatting helpers for the read-only Streamlit console."""

from __future__ import annotations

from typing import Any

from eventalpha.briefing.builder import (
    _aggregate_rule_updates,
    _dedupe_event_cards,
    _dedupe_review_results,
)
from eventalpha.briefing.presentation import aggregate_messages, extract_prediction_ids_from_notes

FORBIDDEN_TRADING_TERMS = ("买入", "卖出", "目标价")


def format_percent(value: Any, *, digits: int = 2) -> str:
    """Format a numeric return/ratio as a percentage."""
    if value is None or value == "":
        return "暂无"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return str(value)


def format_bool(value: Any) -> str:
    """Format booleans and SQLite bool-ish values for display."""
    if value in {True, 1, "1", "true", "True"}:
        return "是"
    if value in {False, 0, "0", "false", "False"}:
        return "否"
    return "暂无"


def aggregate_warnings(values: list[str], *, limit: int = 3) -> list[str]:
    """Aggregate warning text for compact display."""
    return aggregate_messages(values, limit=limit)


def dedupe_event_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return EventCards after Phase 7A.1 deduplication."""
    deduped, _ = _dedupe_event_cards(rows)
    return deduped


def dedupe_review_results(rows: list[dict[str, Any]], recent_runs: list[Any] | None = None) -> list[dict[str, Any]]:
    """Return ReviewResults deduped by prediction/asset/horizon."""
    latest_auto_review = next((run for run in recent_runs or [] if run.job_type == "auto_review_runner"), None)
    preferred_ids = extract_prediction_ids_from_notes(latest_auto_review.notes if latest_auto_review else [])
    deduped, _ = _dedupe_review_results(rows, preferred_prediction_ids=preferred_ids)
    return deduped


def aggregate_rule_updates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return RuleUpdates grouped by rule/action."""
    return _aggregate_rule_updates(rows)


def format_event_card(row: dict[str, Any]) -> dict[str, Any]:
    """Format one EventCard row for UI tables/cards."""
    return {
        "卡片ID": row.get("card_id") or "暂无",
        "事件ID": row.get("event_id") or "暂无",
        "等级": row.get("event_level") or "暂无",
        "标题": row.get("event_title") or "Untitled event",
        "摘要": row.get("one_sentence") or "暂无",
        "风险": list(row.get("risk_factors") or []),
        "验证": list(row.get("verification_indicators") or []),
        "重复数": int(row.get("duplicate_count") or 1),
        "可信度": row.get("credibility_score"),
        "历史验证": row.get("history_validation_summary") or "暂无",
        "创建时间": row.get("created_at") or "暂无",
    }


def format_lifecycle_event(event: Any, urgency_by_id: dict[str, Any] | None = None) -> dict[str, Any]:
    """Format one TrackedEvent for UI display."""
    latest = event.timeline[-1] if getattr(event, "timeline", []) else None
    score = (urgency_by_id or {}).get(event.tracked_event_id)
    return {
        "事件ID": event.tracked_event_id,
        "标题": event.canonical_title,
        "摘要": event.current_summary or "暂无",
        "阶段": event.lifecycle_stage,
        "来源数": event.source_count,
        "可信度": event.credibility_status or "暂无",
        "官方证据": event.official_evidence_status or "暂无",
        "最近出现": str(event.last_seen_at),
        "最新更新": latest.update_type if latest else "暂无",
        "来源": ", ".join(event.sources[:3]) if event.sources else "暂无",
        "优先级": score.urgency_level if score else "暂无",
        "优先分": score.urgency_score if score else None,
        "背景分析": event.lifecycle_stage == "analysis_only",
    }


def format_review_result(row: dict[str, Any]) -> dict[str, Any]:
    """Format one ReviewResult row for UI display."""
    return {
        "ReviewID": row.get("review_id") or "暂无",
        "PredictionID": row.get("prediction_id") or "暂无",
        "资产": row.get("asset_name") or "暂无",
        "窗口": row.get("horizon") or "暂无",
        "因果有效性": row.get("causal_validity") or "unknown",
        "方向正确": format_bool(row.get("direction_correct")),
        "实际收益": format_percent(row.get("actual_return")),
        "基准收益": format_percent(row.get("benchmark_return")),
        "超额收益": format_percent(row.get("excess_return")),
        "错误类型": row.get("error_type") or "none",
        "重复数": int(row.get("duplicate_count") or 1),
        "创建时间": row.get("created_at") or "暂无",
    }


def format_rule_update(row: dict[str, Any]) -> dict[str, Any]:
    """Format one aggregated RuleUpdate row."""
    return {
        "UpdateID": row.get("update_id") or "暂无",
        "RuleID": row.get("rule_id") or "rule_update",
        "动作": row.get("update_action") or "unchanged",
        "次数": int(row.get("count") or 1),
        "旧权重": row.get("old_weight"),
        "新权重": row.get("new_weight"),
        "理由": row.get("reason") or "暂无",
        "创建时间": row.get("created_at") or "暂无",
    }


def format_scheduler_run(run: Any) -> dict[str, Any]:
    """Format one SchedulerRunRecord."""
    return {
        "RunID": run.run_id,
        "任务": run.job_type,
        "状态": run.status,
        "开始时间": str(run.started_at),
        "候选数": run.candidate_items,
        "分析数": run.analyzed_events,
        "生命周期更新": run.lifecycle_updates,
        "Warnings": "; ".join(aggregate_messages(run.warnings, limit=2)),
        "Errors": "; ".join(aggregate_messages(run.errors, limit=2)),
    }


def format_tracking_policy(policy: Any, title_by_id: dict[str, str] | None = None) -> dict[str, Any]:
    """Format one TrackingPolicy."""
    return {
        "事件ID": policy.tracked_event_id,
        "标题": (title_by_id or {}).get(policy.tracked_event_id, policy.tracked_event_id),
        "模式": policy.tracking_mode,
        "间隔分钟": policy.scan_interval_minutes,
        "是否分析": format_bool(policy.analyze),
        "原因": policy.reason,
    }


def contains_forbidden_trading_terms(value: str) -> bool:
    """Return True if display text contains disallowed trading instruction terms."""
    return any(term in value for term in FORBIDDEN_TRADING_TERMS)
