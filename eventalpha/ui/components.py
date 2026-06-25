"""Pure data builders for the Streamlit event console."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel, RISK_DISCLAIMER
from eventalpha.reasoning import build_causal_evidence_summary
from eventalpha.learning import load_rule_feedback_signals

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
    source_kind: str = "real"
    source_label: str = "本地落盘数据"


class EventConsoleData(EventAlphaModel):
    """UI-ready page data."""

    dashboard: DashboardSummary
    source_kind: str = "real"
    source_label: str = "本地落盘数据"
    daily_briefing_markdown: str
    daily_briefing_json: dict[str, Any] = Field(default_factory=dict)
    daily_briefing_preview: dict[str, Any] = Field(default_factory=dict)
    event_cards: list[dict[str, Any]] = Field(default_factory=list)
    event_card_duplicate_total: int = 0
    prediction_ledger_rows: list[dict[str, Any]] = Field(default_factory=list)
    asset_signal_rows: list[dict[str, Any]] = Field(default_factory=list)
    causal_chain_view: dict[str, Any] = Field(default_factory=dict)
    lifecycle_summary: dict[str, Any] = Field(default_factory=dict)
    lifecycle_events: list[dict[str, Any]] = Field(default_factory=list)
    background_events: list[dict[str, Any]] = Field(default_factory=list)
    review_results: list[dict[str, Any]] = Field(default_factory=list)
    review_summary: dict[str, Any] = Field(default_factory=dict)
    rule_updates: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_runs: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_jobs: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_status_rows: list[dict[str, Any]] = Field(default_factory=list)
    scheduler_status_counts: dict[str, int] = Field(default_factory=dict)
    scheduler_job_type_counts: dict[str, int] = Field(default_factory=dict)
    scheduler_warnings: list[str] = Field(default_factory=list)
    friendly_scheduler_warnings: list[str] = Field(default_factory=list)
    tracking_policies: list[dict[str, Any]] = Field(default_factory=list)
    historical_cases: list[dict[str, Any]] = Field(default_factory=list)
    historical_case_summary: dict[str, Any] = Field(default_factory=dict)
    source_coverage_summary: dict[str, Any] = Field(default_factory=dict)
    search_quality_summary: dict[str, Any] = Field(default_factory=dict)
    rule_feedback_summary: dict[str, Any] = Field(default_factory=dict)
    push_outbox_summary: dict[str, Any] = Field(default_factory=dict)
    causal_evidence_rows: list[dict[str, Any]] = Field(default_factory=list)
    causal_evidence_summary: dict[str, Any] = Field(default_factory=dict)
    raw_debug: dict[str, Any] = Field(default_factory=dict)
    data_status: dict[str, Any] = Field(default_factory=dict)
    page_updated_at: str = "未记录"
    notes: list[str] = Field(default_factory=list)


def build_dashboard_summary(bundle: dict[str, Any]) -> DashboardSummary:
    """Build dashboard metrics from loaded local data."""
    data = bundle["collected_data"]
    source_kind, source_label = _bundle_source(bundle)
    urgency_counts = Counter(score.urgency_level for score in data.urgency_scores)
    latest_auto_review = next((run for run in data.recent_runs if run.job_type == "auto_review_runner"), None)
    review_result_count = _count_from_notes(latest_auto_review.notes if latest_auto_review else [], "ReviewResult count")
    rule_update_count = _count_from_notes(latest_auto_review.notes if latest_auto_review else [], "RuleUpdate count")
    review_result_count = review_result_count or len(data.review_results)
    rule_update_count = rule_update_count or len(data.rule_updates)
    report = bundle.get("latest_report")

    raw_warnings = aggregate_warnings(bundle.get("warnings", []), limit=3)
    top_events = bundle.get("top_events") or _build_top_events(
        data,
        source_kind=source_kind,
        source_label="Lifecycle Store" if source_kind == "real" else "Demo Lifecycle Store",
    )
    recent_reviews = bundle.get("recent_reviews") or _build_recent_reviews(data)
    recent_rule_updates = bundle.get("recent_rule_updates") or _build_recent_rule_updates(data)
    friendly_warnings = bundle.get("friendly_warnings") or format_warning_friendly(raw_warnings)

    status_notes = [
        _latest_run_note("scheduler_status", data.recent_runs),
        _latest_run_note("auto_review_runner", data.recent_runs),
        "当前页面展示本地 Demo 数据，不代表真实市场结论。"
        if source_kind == "demo"
        else "当前页面展示本地持久化结果，不代表真实市场结论。",
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
        source_kind=source_kind,
        source_label=source_label,
    )


def build_page_data(bundle: dict[str, Any]) -> EventConsoleData:
    """Build all page data in one pure function."""
    data = bundle["collected_data"]
    source_kind, source_label = _bundle_source(bundle)
    urgency_by_id = {score.tracked_event_id: score for score in data.urgency_scores}
    title_by_id = {event.tracked_event_id: event.canonical_title for event in data.active_events}
    lifecycle_rows = [format_lifecycle_event(event, urgency_by_id) for event in data.active_events]
    lifecycle_rows = [_with_source(row, source_kind, "Lifecycle Store" if source_kind == "real" else "Demo Lifecycle Store") for row in lifecycle_rows]
    deduped_cards = dedupe_event_cards(data.event_cards)
    event_details = _event_details_by_id(bundle.get("event_card_details", []))
    event_card_duplicate_total = sum(max(int(row.get("duplicate_count") or 1) - 1, 0) for row in deduped_cards)
    event_card_rows = [
        _format_event_card_with_details(row, event_details, source_kind, source_label)
        for row in deduped_cards
    ]
    review_rows = [
        _with_source(format_review_result(row), source_kind, "ReviewResult" if source_kind == "real" else "Demo ReviewResult")
        for row in dedupe_review_results(data.review_results, recent_runs=data.recent_runs)
    ]
    rule_rows = [
        _with_source(format_rule_update(row), source_kind, "RuleUpdate" if source_kind == "real" else "Demo RuleUpdate")
        for row in aggregate_rule_updates(data.rule_updates)
    ]
    report = bundle.get("latest_report")
    warnings = aggregate_warnings(data.warnings, limit=3)
    ledger_rows = _build_prediction_ledger_rows(
        bundle.get("prediction_ledger_rows", []),
        source_kind=source_kind,
        source_label="Prediction Ledger" if source_kind == "real" else "Demo Prediction Ledger",
    )
    lifecycle_summary = _build_lifecycle_summary(lifecycle_rows, source_kind=source_kind)
    market_mapping_rows = bundle.get("market_mappings", [])
    asset_signal_rows = _build_asset_signal_rows(
        event_card_rows=event_card_rows,
        ledger_rows=ledger_rows,
        market_mapping_rows=market_mapping_rows,
        source_kind=source_kind,
    )
    causal_chain_view = _build_causal_chain_view(
        event_cards=event_card_rows,
        ledger_rows=ledger_rows,
        source_kind=source_kind,
    )
    scheduler_status_rows = _build_scheduler_status_rows(data, source_kind=source_kind)
    daily_briefing_preview = _build_daily_briefing_preview(report, source_kind=source_kind)
    historical_cases = _build_historical_case_rows(
        bundle.get("historical_cases", []),
        source_kind=source_kind,
    )
    feedback_signals = load_rule_feedback_signals(
        review_results=review_rows,
        rule_updates=rule_rows,
        ledger_rows=ledger_rows,
    )
    causal_evidence = _build_causal_evidence_for_events(
        event_card_rows,
        historical_cases=historical_cases,
        review_rows=review_rows,
        ledger_rows=ledger_rows,
    )
    capability_reports = bundle.get("capability_reports", {})
    return EventConsoleData(
        dashboard=build_dashboard_summary(bundle),
        source_kind=source_kind,
        source_label=source_label,
        daily_briefing_markdown=report.markdown if report else "",
        daily_briefing_json=report.json_payload if report else {},
        daily_briefing_preview=daily_briefing_preview,
        event_cards=event_card_rows,
        event_card_duplicate_total=event_card_duplicate_total,
        prediction_ledger_rows=ledger_rows,
        asset_signal_rows=asset_signal_rows,
        causal_chain_view=causal_chain_view,
        lifecycle_summary=lifecycle_summary,
        lifecycle_events=[row for row in lifecycle_rows if not row["背景分析"]],
        background_events=[row for row in lifecycle_rows if row["背景分析"]],
        review_results=review_rows,
        review_summary=_build_review_summary(review_rows),
        rule_updates=rule_rows,
        scheduler_runs=[format_scheduler_run(run) for run in data.recent_runs],
        scheduler_jobs=[job.model_dump(mode="json") for job in data.scheduler_jobs],
        scheduler_status_rows=scheduler_status_rows,
        scheduler_status_counts=dict(Counter(run.status for run in data.recent_runs)),
        scheduler_job_type_counts=dict(Counter(run.job_type for run in data.recent_runs)),
        scheduler_warnings=warnings,
        friendly_scheduler_warnings=format_warning_friendly(warnings),
        tracking_policies=[
            format_tracking_policy(policy, title_by_id)
            for policy in data.tracking_policies
        ],
        historical_cases=historical_cases,
        historical_case_summary=_build_historical_case_summary(historical_cases),
        source_coverage_summary=_build_source_coverage_summary(capability_reports.get("source_coverage", {})),
        search_quality_summary=_build_search_quality_summary(capability_reports.get("search_quality", {})),
        rule_feedback_summary=_build_rule_feedback_summary(capability_reports.get("rule_feedback", {}), feedback_signals),
        push_outbox_summary=_build_push_outbox_summary(capability_reports.get("push_outbox", {})),
        causal_evidence_rows=causal_evidence["rows"],
        causal_evidence_summary=causal_evidence["summary"],
        raw_debug={
            "scheduler_status_counts": dict(Counter(run.status for run in data.recent_runs)),
            "scheduler_job_type_counts": dict(Counter(run.job_type for run in data.recent_runs)),
            "notes": list(bundle.get("notes", [])),
            "raw_warnings": warnings,
            "source_kind": source_kind,
            "capability_reports": capability_reports,
        },
        data_status=_build_data_status(bundle, data, source_kind=source_kind),
        page_updated_at=_page_updated_at(bundle, data),
        notes=list(bundle.get("notes", [])),
    )


def _build_top_events(
    data: Any,
    *,
    limit: int = 3,
    source_kind: str = "real",
    source_label: str = "Lifecycle Store",
) -> list[dict[str, Any]]:
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
        row = _with_source(row, source_kind, source_label)
        candidates.append((score.urgency_score, row))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in candidates[:limit]]


def _build_recent_reviews(
    data: Any,
    *,
    limit: int = 5,
    source_kind: str = "real",
    source_label: str | None = None,
) -> list[dict[str, Any]]:
    label = source_label or ("ReviewResult" if source_kind == "real" else "Demo ReviewResult")
    return [
        _with_source(format_review_result(row), source_kind, label)
        for row in dedupe_review_results(data.review_results, recent_runs=data.recent_runs)[:limit]
    ]


def _build_recent_rule_updates(
    data: Any,
    *,
    limit: int = 3,
    source_kind: str = "real",
    source_label: str | None = None,
) -> list[dict[str, Any]]:
    label = source_label or ("RuleUpdate" if source_kind == "real" else "Demo RuleUpdate")
    return [_with_source(format_rule_update(row), source_kind, label) for row in aggregate_rule_updates(data.rule_updates)[:limit]]


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
        "提示": "复盘结果来自本地 ReviewResult；无结果时显示空状态。",
    }


def _bundle_source(bundle: dict[str, Any]) -> tuple[str, str]:
    kind = str(bundle.get("source_kind") or "real")
    if kind not in {"real", "demo", "placeholder"}:
        kind = "real"
    default_label = {
        "real": "本地落盘数据",
        "demo": "本地 Demo 数据",
        "placeholder": "待接入",
    }[kind]
    return kind, str(bundle.get("source_label") or default_label)


def _with_source(row: dict[str, Any], source_kind: str, source_label: str) -> dict[str, Any]:
    result = dict(row)
    result["source_kind"] = source_kind
    result["source_label"] = source_label
    result["来源标签"] = source_label
    return result


def _event_details_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in (row.get("card_id"), row.get("event_id")):
            if key:
                details[str(key)] = row
    return details


def _format_event_card_with_details(
    row: dict[str, Any],
    details_by_id: dict[str, dict[str, Any]],
    source_kind: str,
    source_label: str,
) -> dict[str, Any]:
    merged = dict(row)
    details = details_by_id.get(str(row.get("card_id"))) or details_by_id.get(str(row.get("event_id"))) or {}
    for key in (
        "causal_chain_summary",
        "possible_impacts",
        "sources",
        "what_happened",
        "history_validation_summary",
    ):
        if key in details and not merged.get(key):
            merged[key] = details.get(key)
    formatted = format_event_card(merged)
    formatted["因果链摘要"] = list(merged.get("causal_chain_summary") or [])
    formatted["信息来源"] = list(merged.get("sources") or [])
    formatted["事实经过"] = merged.get("what_happened") or "暂无"
    return _with_source(
        formatted,
        source_kind,
        "EventCard" if source_kind == "real" else "Demo EventCard",
    )


def _build_prediction_ledger_rows(
    rows: list[dict[str, Any]],
    *,
    source_kind: str,
    source_label: str,
) -> list[dict[str, Any]]:
    formatted: list[dict[str, Any]] = []
    for row in rows:
        # These values are copied directly from prediction_ledger / predicted_assets.
        # Missing fields are intentionally shown as "未记录" instead of inferred.
        formatted.append(
            _with_source(
                {
                    "PredictionID": row.get("prediction_id") or "未记录",
                    "事件ID": row.get("event_id") or "未记录",
                    "事件": row.get("event_title") or "未记录",
                    "事件类型": row.get("event_type") or "未记录",
                    "事件等级": row.get("event_level") or "未记录",
                    "资产": row.get("asset_name") or "未记录",
                    "资产类型": row.get("asset_type") or "未记录",
                    "方向": row.get("direction") or "未记录",
                    "时间窗口": row.get("time_window") or "未记录",
                    "因果置信度": row.get("chain_confidence"),
                    "反伪相关后置信度": row.get("anti_spurious_adjusted_confidence"),
                    "最终置信度": row.get("final_confidence") if row.get("final_confidence") is not None else row.get("confidence"),
                    "基准": row.get("benchmark") or "未记录",
                    "状态": row.get("status") or "未记录",
                    "发布时间": row.get("publish_time") or "未记录",
                    "创建时间": row.get("prediction_created_at") or row.get("created_at") or "未记录",
                },
                source_kind,
                source_label,
            )
        )
    return formatted


def _build_asset_signal_rows(
    *,
    event_card_rows: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
    market_mapping_rows: list[dict[str, Any]],
    source_kind: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for ledger in ledger_rows:
        asset = _clean_value(ledger.get("资产"))
        event = _clean_value(ledger.get("事件"))
        if not asset or not event:
            continue
        key = (asset, event)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            _with_source(
                {
                    "资产/板块": asset,
                    "关联事件": event,
                    "影响方向": _direction_label(ledger.get("方向")),
                    "信号来源": "Prediction Ledger",
                },
                ledger.get("source_kind") or source_kind,
                "Prediction Ledger",
            )
        )
        if len(rows) >= limit:
            return rows

    for card in event_card_rows:
        event = _clean_value(card.get("标题"))
        for asset in list(card.get("可能影响资产") or [])[:3]:
            asset_text = _clean_value(asset)
            if not asset_text or not event:
                continue
            key = (asset_text, event)
            if key in seen:
                continue
            seen.add(key)
            # EventCard only records impacted assets, not live prices. The signal is
            # deliberately a research label derived from the card mapping.
            rows.append(
                _with_source(
                    {
                        "资产/板块": asset_text,
                        "关联事件": event,
                        "影响方向": "关注度上升",
                        "信号来源": "EventCard 映射",
                    },
                    card.get("source_kind") or source_kind,
                    "EventCard 映射" if source_kind == "real" else "Demo EventCard 映射",
                )
            )
            if len(rows) >= limit:
                return rows

    for mapping in market_mapping_rows:
        event = _clean_value(mapping.get("event_title") or mapping.get("event_id"))
        for asset in _mapped_asset_names(mapping.get("mapped_assets")):
            key = (asset, event)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                _with_source(
                    {
                        "资产/板块": asset,
                        "关联事件": event or "未记录",
                        "影响方向": "事件映射",
                        "信号来源": "Market Mapping",
                    },
                    source_kind,
                    "Market Mapping" if source_kind == "real" else "Demo Market Mapping",
                )
            )
            if len(rows) >= limit:
                return rows

    if rows:
        return rows
    return [
        _with_source(row, "demo", "Demo Signal")
        for row in [
            {"资产/板块": "半导体", "关联事件": "AI芯片出口管制", "影响方向": "关注度上升", "信号来源": "Demo Signal"},
            {"资产/板块": "原油", "关联事件": "中东局势升温", "影响方向": "风险上行", "信号来源": "Demo Signal"},
            {"资产/板块": "黄金", "关联事件": "避险情绪", "影响方向": "避险关注", "信号来源": "Demo Signal"},
            {"资产/板块": "AI算力", "关联事件": "国产替代预期", "影响方向": "关注度上升", "信号来源": "Demo Signal"},
        ]
    ]


def _build_causal_chain_view(
    *,
    event_cards: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
    source_kind: str,
) -> dict[str, Any]:
    for card in event_cards:
        chain = [str(item) for item in card.get("因果链摘要") or [] if str(item).strip()]
        if not chain:
            continue
        title = _clean_value(card.get("标题")) or "当前重点事件"
        nodes = _chain_nodes_from_summary(title, chain, card.get("可能影响资产") or [])
        return _with_source(
            {
                "title": title,
                "nodes": nodes,
                "caption": " → ".join([node.get("label", "") for node in nodes if node.get("label")]),
            },
            card.get("source_kind") or source_kind,
            "来自当前重点事件",
        )

    if ledger_rows:
        first = ledger_rows[0]
        title = _clean_value(first.get("事件")) or "当前预测事件"
        asset = _clean_value(first.get("资产")) or "相关资产"
        direction = _direction_label(first.get("方向"))
        return _with_source(
            {
                "title": title,
                "nodes": [
                    {"icon": "事件", "label": title},
                    {"icon": "变量", "label": first.get("事件类型") or "影响变量未记录"},
                    {"icon": "行业", "label": first.get("资产类型") or "行业未记录"},
                    {"icon": "资产", "label": f"{asset} / {direction}"},
                ],
                "caption": f"{title} → {asset}（来自 Prediction Ledger 字段，不补造因果细节）",
            },
            first.get("source_kind") or source_kind,
            "来自当前重点事件",
        )

    return _with_source(
        {
            "title": "Demo Chain",
            "nodes": [
                {"icon": "事件", "label": "AI芯片出口管制"},
                {"icon": "变量", "label": "海外GPU供应受限"},
                {"icon": "行业", "label": "国产替代预期"},
                {"icon": "资产", "label": "国产AI芯片/服务器"},
            ],
            "caption": "Demo Chain：示例链路，不代表真实运行结果。",
        },
        "demo",
        "Demo Chain",
    )


def _chain_nodes_from_summary(title: str, chain: list[str], assets: list[Any]) -> list[dict[str, str]]:
    variable = chain[0] if len(chain) >= 1 else "变量未记录"
    industry = chain[1] if len(chain) >= 2 else (chain[-1] if chain else "行业未记录")
    asset = _clean_value(assets[0]) if assets else (chain[-1] if chain else "资产未记录")
    return [
        {"icon": "事件", "label": title},
        {"icon": "变量", "label": variable},
        {"icon": "行业", "label": industry},
        {"icon": "资产", "label": asset or "资产未记录"},
    ]


def _build_lifecycle_summary(
    rows: list[dict[str, Any]],
    *,
    source_kind: str,
) -> dict[str, Any]:
    counts = Counter(str(row.get("阶段") or "unknown") for row in rows)
    total = len(rows)
    tracked_count = counts.get("new", 0) + counts.get("developing", 0) + counts.get("confirmed", 0)
    stages = [] if not total else [
        {"label": "已发现", "count": total},
        {"label": "已验证", "count": counts.get("confirmed", 0)},
        {"label": "已分析", "count": counts.get("analysis_only", 0)},
        {"label": "已发布", "count": "--"},
        {"label": "跟踪中", "count": tracked_count},
        {"label": "已复盘", "count": "--"},
    ]
    current_events = [
        {
            "标题": row.get("短标题") or row.get("标题"),
            "阶段": row.get("阶段"),
            "阶段说明": row.get("阶段说明"),
            "来源标签": row.get("source_label"),
        }
        for row in rows[:3]
    ]
    return _with_source(
        {
            "total": total,
            "stages": stages,
            "current_events": current_events,
        },
        source_kind,
        "Lifecycle Store" if source_kind == "real" else "Demo Lifecycle Store",
    )


def _build_daily_briefing_preview(report: Any, *, source_kind: str) -> dict[str, Any]:
    if not report:
        return _with_source(
            {
                "has_report": False,
                "title": "暂无今日简报",
                "date": None,
                "path": None,
                "excerpt": "暂无今日简报，请点击生成今日简报或运行 daily_briefing job。",
            },
            "placeholder",
            "暂无数据",
        )
    title = _briefing_title(report)
    excerpt = _markdown_excerpt(report.markdown)
    return _with_source(
        {
            "has_report": True,
            "title": title,
            "date": report.briefing_date.isoformat() if isinstance(report.briefing_date, date) else str(report.briefing_date or "未记录"),
            "path": report.markdown_path,
            "excerpt": excerpt,
        },
        source_kind,
        "Daily Briefing Report" if source_kind == "real" else "Demo Daily Briefing Report",
    )


def _build_historical_case_rows(rows: list[dict[str, Any]], *, source_kind: str) -> list[dict[str, Any]]:
    formatted: list[dict[str, Any]] = []
    for row in rows:
        outcome = row.get("outcome") if isinstance(row.get("outcome"), dict) else {}
        assessment = row.get("causal_assessment") if isinstance(row.get("causal_assessment"), dict) else {}
        row_source_kind = "demo" if _is_demo_historical_case(row) else source_kind
        source_label = "Demo Historical Case" if row_source_kind == "demo" else "Historical Case Store"
        formatted.append(
            _with_source(
                {
                    "CaseID": row.get("case_id") or "未记录",
                    "案例名称": row.get("title") or "未记录",
                    "事件类型": row.get("event_type") or "未记录",
                    "事件日期": row.get("event_date") or "未记录",
                    "地区": row.get("region") or "未记录",
                    "摘要": row.get("summary") or "未记录",
                    "实体": list(row.get("entities") or []),
                    "行业": list(row.get("industries") or []),
                    "影响资产": list(row.get("affected_assets") or []),
                    "因果链摘要": list(row.get("causal_chain_summary") or []),
                    "标签": list(row.get("tags") or []),
                    "来源说明": list(row.get("source_notes") or []),
                    "结果质量": outcome.get("outcome_quality") or "未记录",
                    "市场反应": outcome.get("market_reaction_summary") or "未记录",
                    "基准": outcome.get("benchmark") or "未记录",
                    "资产收益": outcome.get("asset_returns") or {},
                    "预期方向": assessment.get("expected_direction") or "未记录",
                    "实际方向": assessment.get("realized_direction") or "未记录",
                    "因果有效性": assessment.get("causal_validity") or "unknown",
                    "有效经验": list(assessment.get("what_worked") or []),
                    "失效原因": list(assessment.get("what_failed") or []),
                    "经验教训": list(assessment.get("lessons") or []),
                },
                row_source_kind,
                source_label,
            )
        )
    return formatted


def _build_historical_case_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    event_types = {row.get("事件类型") for row in rows if _clean_value(row.get("事件类型"))}
    with_outcome = [row for row in rows if row.get("市场反应") not in {None, "", "未记录"} or row.get("资产收益")]
    verifiable = [
        row
        for row in rows
        if row.get("因果有效性") not in {None, "", "unknown", "未记录"}
        or row.get("结果质量") not in {None, "", "未记录"}
    ]
    latest_date = max((str(row.get("事件日期") or "") for row in rows), default="--")
    return {
        "历史案例数": len(rows),
        "事件类型数": len(event_types),
        "已有 outcome": len(with_outcome),
        "可验证案例": len(verifiable),
        "最近案例日期": latest_date or "--",
    }


def _build_causal_evidence_for_events(
    event_cards: list[dict[str, Any]],
    *,
    historical_cases: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for card in event_cards[:5]:
        summary = build_causal_evidence_summary(
            card,
            historical_cases=historical_cases,
            review_results=review_rows,
            ledger_rows=ledger_rows,
        )
        for item in summary.items:
            row = item.model_dump(mode="json")
            row["事件"] = summary.event_title
            row["事件ID"] = summary.event_id or "未记录"
            row["source_kind"] = summary.source_kind
            row["source_label"] = summary.source_label
            rows.append(row)
    evidence_counts = Counter(row.get("evidence_type") or "unknown" for row in rows)
    return {
        "rows": rows,
        "summary": _with_source(
            {
                "total": len(rows),
                "source": evidence_counts.get("source", 0),
                "historical_case": evidence_counts.get("historical_case", 0),
                "market_data": evidence_counts.get("market_data", 0),
                "assumption": evidence_counts.get("assumption", 0),
                "missing": evidence_counts.get("missing", 0),
                "notes": "证据层仅使用本地 EventCard / HistoricalCase / ReviewResult / Prediction Ledger 数据。",
            },
            "real",
            "Causal Evidence Layer",
        ),
    }


def _build_source_coverage_summary(report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return _with_source(
            {
                "title": "信息源覆盖状态",
                "status": "暂无报告",
                "enabled_count": "--",
                "ok_count": "--",
                "failed_count": "--",
                "placeholder_count": "--",
                "path": "暂无",
                "items": [],
            },
            "placeholder",
            "Source Coverage 待生成",
        )
    return _with_source(
        {
            "title": "信息源覆盖状态",
            "status": "已生成",
            "enabled_count": report.get("enabled_count", 0),
            "ok_count": report.get("ok_count", 0),
            "failed_count": report.get("failed_count", 0),
            "placeholder_count": report.get("placeholder_count", 0),
            "path": report.get("_path") or "未记录",
            "items": list(report.get("items") or [])[:6],
        },
        "demo" if report.get("demo_mode") else "real",
        "Source Coverage Report",
    )


def _build_search_quality_summary(report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return _with_source(
            {
                "title": "搜索质量评估",
                "status": "暂无报告",
                "raw_news_count": "--",
                "after_dedup_count": "--",
                "cluster_count": "--",
                "event_card_count": "--",
                "ledger_prediction_count": "--",
                "path": "暂无",
            },
            "placeholder",
            "Search Quality 待生成",
        )
    return _with_source(
        {
            "title": "搜索质量评估",
            "status": "已生成",
            "raw_news_count": report.get("raw_news_count", 0),
            "after_dedup_count": report.get("after_dedup_count", 0),
            "cluster_count": report.get("cluster_count", 0),
            "event_card_count": report.get("event_card_count", 0),
            "ledger_prediction_count": report.get("ledger_prediction_count", 0),
            "path": report.get("_path") or "未记录",
        },
        "demo" if report.get("demo_mode") else "real",
        "Search Quality Report",
    )


def _build_rule_feedback_summary(
    report: dict[str, Any],
    feedback_signals: list[Any],
) -> dict[str, Any]:
    report_signals = list(report.get("signals") or []) if report else []
    signals = report_signals or [signal.model_dump(mode="json") for signal in feedback_signals]
    source_kind = "demo" if report.get("demo_mode") else "real" if signals else "placeholder"
    return _with_source(
        {
            "title": "复盘反馈信号",
            "status": "已生成" if report else ("本地计算" if signals else "暂无报告"),
            "signal_count": len(signals),
            "positive_count": sum(1 for signal in signals if float(signal.get("adjustment") or 0) > 0),
            "negative_count": sum(1 for signal in signals if float(signal.get("adjustment") or 0) < 0),
            "needs_verification_count": sum(1 for signal in signals if signal.get("needs_verification")),
            "path": report.get("_path") if report else "本地 UI 计算，未写报告",
            "signals": signals[:6],
        },
        source_kind,
        "Rule Feedback Signals" if signals else "Rule Feedback 待生成",
    )


def _build_push_outbox_summary(report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return _with_source(
            {
                "title": "推送 Outbox",
                "status": "暂无报告",
                "message_count": "--",
                "channel_note": "微信通道当前为 placeholder，待生成 outbox。",
                "path": "暂无",
            },
            "placeholder",
            "Push Outbox 待生成",
        )
    return _with_source(
        {
            "title": "推送 Outbox",
            "status": "已生成",
            "message_count": report.get("message_count", 0),
            "channel_note": report.get("channel_note") or "微信通道当前为 placeholder。",
            "path": report.get("_path") or "未记录",
        },
        "demo" if report.get("demo_mode") else "real",
        "Push Outbox Report",
    )


def _is_demo_historical_case(row: dict[str, Any]) -> bool:
    outcome = row.get("outcome") if isinstance(row.get("outcome"), dict) else {}
    tags = " ".join(str(item) for item in row.get("tags") or [])
    notes = " ".join(str(item) for item in row.get("source_notes") or [])
    quality = str(outcome.get("outcome_quality") or "")
    text = f"{tags} {notes} {quality}".casefold()
    return "demo" in text or "manual_seed" in text or "illustrative" in text


def _build_scheduler_status_rows(data: Any, *, source_kind: str) -> list[dict[str, Any]]:
    job_labels = [
        ("news_lifecycle_scan", "新闻生命周期扫描"),
        ("candidate_analysis", "候选事件分析"),
        ("urgent_event_scan", "紧急事件扫描 / urgent_tracking"),
        ("auto_review_runner", "自动复盘"),
        ("daily_briefing", "每日简报"),
        ("rule_update_checker", "规则更新检查"),
    ]
    runs_by_type: dict[str, Any] = {}
    for run in data.recent_runs:
        runs_by_type.setdefault(run.job_type, run)
    configs_by_type: dict[str, Any] = {}
    for job in data.scheduler_jobs:
        configs_by_type.setdefault(job.job_type, job)

    rows: list[dict[str, Any]] = []
    for job_type, label in job_labels:
        run = runs_by_type.get(job_type)
        config = configs_by_type.get(job_type)
        if run:
            status = _scheduler_status_label(run.status)
            source = "scheduler_runs.jsonl"
            row_source_kind = source_kind
        elif config:
            status = "等待中" if getattr(config, "enabled", True) else "已禁用"
            source = "scheduler_state.json"
            row_source_kind = source_kind
        elif job_type == "rule_update_checker":
            status = "待接入"
            source = "待接入"
            row_source_kind = "placeholder"
        else:
            status = "未运行"
            source = "scheduler_state/runs"
            row_source_kind = source_kind
        rows.append(
            _with_source(
                {
                    "任务": label,
                    "job_type": job_type,
                    "最近运行时间": str(getattr(run, "started_at", None) or "未运行"),
                    "最近结果": status,
                    "状态": status,
                    "信号来源": source,
                },
                row_source_kind,
                source,
            )
        )
    return rows


def _build_data_status(bundle: dict[str, Any], data: Any, *, source_kind: str) -> dict[str, Any]:
    raw = dict(bundle.get("data_status") or {})
    configured_sources = _configured_source_label(data.scheduler_jobs)
    return _with_source(
        {
            "reports_count": raw.get("reports_count", len(bundle.get("reports") or [])),
            "latest_report_path": raw.get("latest_report_path") or "暂无",
            "lifecycle_store_exists": bool(raw.get("lifecycle_store_exists")),
            "scheduler_state_exists": bool(raw.get("scheduler_state_exists")),
            "scheduler_runs_exists": bool(raw.get("scheduler_runs_exists")),
            "ledger_exists": bool(raw.get("ledger_exists")),
            "historical_cases_exists": bool(raw.get("historical_cases_exists")),
            "historical_cases_path": raw.get("historical_cases_path") or "暂无",
            "configured_sources": configured_sources,
            "notes": list(bundle.get("notes", []))[:3],
        },
        source_kind,
        "本地数据状态" if source_kind == "real" else "Demo 数据状态",
    )


def _configured_source_label(jobs: list[Any]) -> str:
    sources = {str(getattr(job, "source", "") or "").upper() for job in jobs if getattr(job, "source", None)}
    has_real_fetch = any(bool(getattr(job, "real_fetch", False)) for job in jobs)
    labels: list[str] = []
    if "RSS" in sources:
        labels.append("RSS")
    if has_real_fetch:
        labels.append("GDELT/RSS")
    labels.append("Demo")
    labels.append("本地缓存")
    return " / ".join(dict.fromkeys(labels))


def _scheduler_status_label(status: str) -> str:
    mapping = {
        "success": "成功",
        "dry_run": "演练",
        "failed": "失败",
        "started": "运行中",
        "skipped": "跳过",
    }
    return mapping.get(str(status or ""), str(status or "未运行"))


def _direction_label(value: Any) -> str:
    mapping = {
        "up": "关注度上升",
        "down": "风险下行",
        "neutral": "中性观察",
        "mixed": "分化观察",
        "watch": "观察",
    }
    return mapping.get(str(value or "").casefold(), str(value or "未记录"))


def _mapped_asset_names(value: Any) -> list[str]:
    results: list[str] = []
    for item in value or []:
        if isinstance(item, dict):
            name = item.get("asset_name") or item.get("name") or item.get("asset")
        else:
            name = item
        text = _clean_value(name)
        if text:
            results.append(text)
    return results


def _clean_value(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text in {"暂无", "未记录", "--"} else text


def _page_updated_at(bundle: dict[str, Any], data: Any) -> str:
    candidates: list[str] = []
    report = bundle.get("latest_report")
    if report and getattr(report, "briefing_date", None):
        candidates.append(str(getattr(report, "briefing_date")))
    for run in data.recent_runs[:1]:
        candidates.append(str(getattr(run, "started_at", "") or ""))
    for row in bundle.get("historical_cases", [])[:1]:
        if isinstance(row, dict) and row.get("event_date"):
            candidates.append(str(row.get("event_date")))
    return next((item for item in candidates if item and item != "None"), "未记录")


def _markdown_excerpt(markdown: str, *, limit: int = 140) -> str:
    lines = [line.strip("#- * \t") for line in str(markdown or "").splitlines() if line.strip()]
    text = " ".join(lines[:3]).strip()
    if not text:
        return "报告已生成，但没有可展示预览。"
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


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
