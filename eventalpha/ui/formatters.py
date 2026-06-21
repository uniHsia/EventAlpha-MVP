"""Chinese presentation helpers for the read-only Streamlit console."""

from __future__ import annotations

from typing import Any

from eventalpha.briefing.builder import (
    _aggregate_rule_updates,
    _dedupe_event_cards,
    _dedupe_review_results,
)
from eventalpha.briefing.presentation import aggregate_messages, extract_prediction_ids_from_notes

FORBIDDEN_TRADING_TERMS = ("买入", "卖出", "目标价")
MISSING = "暂无"


def format_priority_label(value: Any) -> str:
    """Format priority/tracking labels in Chinese."""
    mapping = {
        "urgent": "紧急事件",
        "high": "高优先级",
        "normal": "普通跟踪",
        "background": "背景观察",
        "ignore": "暂不跟踪",
        "paused": "暂停跟踪",
        "enhanced": "增强跟踪",
    }
    return mapping.get(str(value or "").casefold(), MISSING)


def format_urgency_label(value: Any) -> str:
    """Format urgency level in Chinese."""
    return format_priority_label(value)


def format_lifecycle_stage(value: Any) -> str:
    """Format lifecycle stage in Chinese."""
    mapping = {
        "new": "新事件",
        "developing": "持续发展",
        "confirmed": "已确认",
        "analysis_only": "背景分析",
        "unconfirmed_or_considering": "待确认",
        "conflicting": "信息冲突",
        "stale": "暂缓跟踪",
        "closed": "已关闭",
        "resolved": "已结束",
    }
    return mapping.get(str(value or "").casefold(), str(value or MISSING))


def format_credibility_label(value: Any) -> str:
    """Format credibility status in Chinese."""
    mapping = {
        "high_confidence": "高可信",
        "multi_source_supported": "多源支持",
        "single_source_low_confidence": "单源低可信",
        "unconfirmed_or_considering": "待确认",
        "analysis_only": "分析/评论",
        "conflicting_claims": "说法冲突",
        "official_source_present": "有官方来源",
    }
    return mapping.get(str(value or "").casefold(), str(value or MISSING))


def format_rule_update_action(value: Any) -> str:
    """Format rule update action in Chinese."""
    mapping = {
        "strengthen": "强化规则",
        "slightly_strengthen": "小幅强化规则",
        "weaken": "削弱规则",
        "keep": "保持规则",
        "unchanged": "保持规则",
        "unknown": "未知动作",
    }
    return mapping.get(str(value or "").casefold(), "未知动作")


def format_return_pct(value: Any, *, digits: int = 2, signed: bool = True) -> str:
    """Format a return ratio as a signed percentage."""
    if value is None or value == "":
        return MISSING
    try:
        number = float(value) * 100
    except (TypeError, ValueError):
        return str(value)
    sign = "+" if signed and number > 0 else ""
    return f"{sign}{number:.{digits}f}%"


def format_percent(value: Any, *, digits: int = 2) -> str:
    """Backward-compatible unsigned-ish percentage formatter."""
    return format_return_pct(value, digits=digits, signed=False)


def format_bool(value: Any) -> str:
    """Format booleans and SQLite bool-ish values for display."""
    if value in {True, 1, "1", "true", "True"}:
        return "是"
    if value in {False, 0, "0", "false", "False"}:
        return "否"
    return MISSING


def format_direction_label(value: Any) -> str:
    """Format direction correctness in Chinese."""
    if value in {True, 1, "1", "true", "True"}:
        return "方向正确"
    if value in {False, 0, "0", "false", "False"}:
        return "方向未验证"
    return "方向待观察"


def format_causal_validity(value: Any) -> str:
    """Format causal validity in Chinese."""
    mapping = {
        "valid": "因果链获得支持",
        "invalid": "市场表现未验证判断",
        "unknown": "观察方向或数据不足",
    }
    return mapping.get(str(value or "unknown").casefold(), "观察方向或数据不足")


def format_error_type(value: Any) -> str:
    """Format review error type in plain Chinese."""
    mapping = {
        "mixed_or_watch_only": "mixed/watch 观察方向，仅记录市场表现",
        "wrong_asset_mapping": "可能需要检查资产映射",
        "none": "暂无错误类型",
        "": "暂无错误类型",
    }
    return mapping.get(str(value or "none").casefold(), str(value))


def format_review_explanation(row: dict[str, Any]) -> str:
    """Build a one-sentence explanation for a ReviewResult."""
    asset = row.get("asset_name") or row.get("资产") or MISSING
    horizon = row.get("horizon") or row.get("窗口") or MISSING
    direction = format_direction_label(row.get("direction_correct"))
    excess = format_return_pct(row.get("excess_return"), signed=True)
    causal = format_causal_validity(row.get("causal_validity"))
    error = format_error_type(row.get("error_type"))
    if row.get("error_type") in {"mixed_or_watch_only", "wrong_asset_mapping"}:
        return f"{asset} / {horizon}：{direction}，超额收益 {excess}，{error}。"
    return f"{asset} / {horizon}：{direction}，超额收益 {excess}，{causal}。"


def format_warning_friendly(values: list[str] | str, *, limit: int = 3) -> list[str]:
    """Convert raw warnings into teacher-friendly status notes."""
    raw_values = [values] if isinstance(values, str) else values
    aggregated = aggregate_messages([str(value) for value in raw_values], limit=limit)
    friendly: list[str] = []
    for warning in aggregated:
        lowered = warning.casefold()
        if "rss query matched no items" in lowered:
            message = "数据源提示：RSS 最近多次未匹配到新闻，不影响本地 demo/mock 流程。"
        elif "feedparser" in lowered:
            message = "数据源提示：RSS 依赖未安装或不可用，不影响本地只读演示。"
        else:
            message = f"系统提示：{warning}"
        if message not in friendly:
            friendly.append(message)
    return friendly


def aggregate_warnings(values: list[str], *, limit: int = 3) -> list[str]:
    """Aggregate warning text for compact raw display."""
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
    duplicate_count = int(row.get("duplicate_count") or 1)
    return {
        "卡片ID": row.get("card_id") or MISSING,
        "事件ID": row.get("event_id") or MISSING,
        "事件等级": row.get("event_level") or MISSING,
        "标题": row.get("event_title") or "Untitled event",
        "一句话摘要": row.get("one_sentence") or MISSING,
        "风险因素": list(row.get("risk_factors") or []),
        "后续验证指标": list(row.get("verification_indicators") or []),
        "重复折叠数": duplicate_count,
        "重复说明": f"已折叠 {duplicate_count} 条相似卡片，当前仅展示最新一条。" if duplicate_count > 1 else "无重复折叠。",
        "可信度": row.get("credibility_score"),
        "历史验证": row.get("history_validation_summary") or MISSING,
        "可能影响资产": list(row.get("possible_impacts") or []),
        "创建时间": row.get("created_at") or MISSING,
    }


def format_lifecycle_event(event: Any, urgency_by_id: dict[str, Any] | None = None) -> dict[str, Any]:
    """Format one TrackedEvent for UI display."""
    latest = event.timeline[-1] if getattr(event, "timeline", []) else None
    score = (urgency_by_id or {}).get(event.tracked_event_id)
    is_background = event.lifecycle_stage == "analysis_only" or (
        score is not None and score.urgency_level in {"background", "ignore"}
    )
    return {
        "事件ID": event.tracked_event_id,
        "标题": event.canonical_title,
        "短标题": _shorten(event.canonical_title, 48),
        "摘要": event.current_summary or MISSING,
        "阶段": event.lifecycle_stage,
        "阶段说明": format_lifecycle_stage(event.lifecycle_stage),
        "来源数": event.source_count,
        "可信度": event.credibility_status or MISSING,
        "可信度说明": format_credibility_label(event.credibility_status),
        "官方证据": event.official_evidence_status or MISSING,
        "最近出现": str(event.last_seen_at),
        "最新变化": latest.update_type if latest else MISSING,
        "来源": ", ".join(event.sources[:3]) if event.sources else MISSING,
        "优先级": score.urgency_level if score else MISSING,
        "优先级说明": format_urgency_label(score.urgency_level if score else None),
        "优先分": score.urgency_score if score else None,
        "重要原因": list(score.reasons[:3]) if score else [],
        "验证指标": list(score.reasons[:2]) if score else [],
        "背景分析": is_background,
    }


def format_review_result(row: dict[str, Any]) -> dict[str, Any]:
    """Format one ReviewResult row for UI display."""
    formatted = {
        "ReviewID": row.get("review_id") or MISSING,
        "PredictionID": row.get("prediction_id") or MISSING,
        "资产": row.get("asset_name") or MISSING,
        "窗口": row.get("horizon") or MISSING,
        "因果有效性": row.get("causal_validity") or "unknown",
        "因果解释": format_causal_validity(row.get("causal_validity")),
        "方向结果": format_direction_label(row.get("direction_correct")),
        "方向正确": format_bool(row.get("direction_correct")),
        "实际收益": format_return_pct(row.get("actual_return"), signed=True),
        "基准收益": format_return_pct(row.get("benchmark_return"), signed=True),
        "超额收益": format_return_pct(row.get("excess_return"), signed=True),
        "超额收益原值": row.get("excess_return"),
        "错误类型": row.get("error_type") or "none",
        "错误解释": format_error_type(row.get("error_type")),
        "重复数": int(row.get("duplicate_count") or 1),
        "创建时间": row.get("created_at") or MISSING,
    }
    formatted["复盘解释"] = format_review_explanation(row)
    return formatted


def format_rule_update(row: dict[str, Any]) -> dict[str, Any]:
    """Format one aggregated RuleUpdate row."""
    count = int(row.get("count") or 1)
    action = row.get("update_action") or "unknown"
    old_weight = row.get("old_weight")
    new_weight = row.get("new_weight")
    return {
        "UpdateID": row.get("update_id") or MISSING,
        "RuleID": row.get("rule_id") or "rule_update",
        "动作": action,
        "动作说明": format_rule_update_action(action),
        "次数": count,
        "旧权重": old_weight,
        "新权重": new_weight,
        "权重变化": f"{old_weight} -> {new_weight}" if old_weight is not None and new_weight is not None else MISSING,
        "理由": row.get("reason") or MISSING,
        "标题": f"{row.get('rule_id') or 'rule_update'} {action} ×{count}" if count > 1 else f"{row.get('rule_id') or 'rule_update'} {action}",
        "中文解释": _rule_update_explanation(row),
        "创建时间": row.get("created_at") or MISSING,
    }


def format_scheduler_run(run: Any) -> dict[str, Any]:
    """Format one SchedulerRunRecord."""
    return {
        "RunID": run.run_id,
        "任务": run.job_type,
        "状态": run.status,
        "状态说明": _scheduler_status_label(run.status),
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
        "模式说明": format_priority_label(policy.tracking_mode),
        "间隔分钟": policy.scan_interval_minutes,
        "是否分析": format_bool(policy.analyze),
        "原因": policy.reason,
    }


def contains_forbidden_trading_terms(value: str) -> bool:
    """Return True if display text contains disallowed trading instruction terms."""
    return any(term in value for term in FORBIDDEN_TRADING_TERMS)


def _rule_update_explanation(row: dict[str, Any]) -> str:
    rule_id = row.get("rule_id") or "rule_update"
    action = row.get("update_action") or "unknown"
    count = int(row.get("count") or 1)
    old_weight = row.get("old_weight")
    new_weight = row.get("new_weight")
    reason = row.get("reason") or "暂无详细理由"
    return f"{rule_id} {format_rule_update_action(action)} ×{count}：{reason}，权重 {old_weight} -> {new_weight}。"


def _scheduler_status_label(status: str) -> str:
    mapping = {
        "success": "成功",
        "dry_run": "演练",
        "failed": "失败",
        "started": "运行中",
        "skipped": "跳过",
    }
    return mapping.get(status, status)


def _shorten(value: str, length: int) -> str:
    text = str(value or "")
    return text if len(text) <= length else f"{text[: length - 1]}…"
