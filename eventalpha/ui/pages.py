"""Streamlit page renderers for the read-only event console."""

from __future__ import annotations

import json
from datetime import date
from html import escape
from typing import Any
from urllib.parse import quote

from eventalpha.briefing import DailyBriefingBuilder, MarkdownBriefingRenderer
from eventalpha.schemas.base import RISK_DISCLAIMER

from .components import EventConsoleData
from .formatters import (
    format_return_pct,
    format_rule_update_action,
)


def render_dashboard(st: Any, page_data: EventConsoleData, *, search_query: str = "") -> None:
    """Render the product-style dashboard page."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    if search_query:
        page_data = _filter_page_data(page_data, search_query)
        st.caption(f"本地搜索结果：{search_query}。仅过滤已加载的 EventCard / Prediction Ledger / ReviewResult / RuleUpdate。")
    st.markdown(_dashboard_shell(page_data, search_query=search_query), unsafe_allow_html=True)
    _render_risk_notice(st)

    if page_data.dashboard.friendly_warnings:
        with st.expander("数据源提示"):
            st.write(page_data.dashboard.friendly_warnings)
            if page_data.dashboard.raw_warnings:
                st.write(page_data.dashboard.raw_warnings)


def render_daily_briefing(
    st: Any,
    page_data: EventConsoleData,
    *,
    collected_data: Any,
    selected_date: date,
) -> None:
    """Render the daily briefing page."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "每日事件研究简报",
        "基于本地事件、复盘结果和调度日志生成的 Markdown 简报。",
        page_data,
        badges=[_source_label(page_data.daily_briefing_preview)],
    )

    action_cols = st.columns([1.1, 1.2, 1.2, 3.8], vertical_alignment="center")
    if action_cols[0].button("刷新 preview", use_container_width=True):
        st.rerun()
    markdown = page_data.daily_briefing_markdown
    json_payload = page_data.daily_briefing_json
    action_cols[1].download_button(
        "下载 Markdown",
        data=markdown or "",
        file_name=f"daily_briefing_{selected_date:%Y%m%d}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    action_cols[2].download_button(
        "下载 JSON",
        data=json.dumps(json_payload, ensure_ascii=False, indent=2),
        file_name=f"daily_briefing_{selected_date:%Y%m%d}.json",
        mime="application/json",
        use_container_width=True,
    )
    action_cols[3].caption(f"原始文件：{page_data.daily_briefing_preview.get('path') or '暂无'}")

    if page_data.scheduler_warnings:
        _render_info_note(st, "数据源提示", "；".join(page_data.friendly_scheduler_warnings or page_data.scheduler_warnings[:2]))
    if not markdown:
        _render_empty_state_html(st, "暂无今日简报，请运行 daily_briefing job 或 run_full_demo。")
        return
    st.markdown(_briefing_sections_html(markdown), unsafe_allow_html=True)
    with st.expander("查看原始 Markdown"):
        st.markdown(markdown)
    _render_risk_notice(st)


def render_event_cards(st: Any, page_data: EventConsoleData) -> None:
    """Render EventCard rows as cards first and table second."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "事件卡片",
        "汇总系统识别出的重点事件、影响链、风险因素和后续验证指标。",
        page_data,
        badges=["EventCard", page_data.source_label],
    )
    rows = page_data.event_cards
    reviewed_event_ids = {row.get("事件ID") for row in page_data.prediction_ledger_rows if row.get("状态") not in {None, "", "未记录", "tracking"}}
    _render_summary_cards(
        st,
        [
            ("事件卡片数", len(rows), "EventCard"),
            ("高优先级事件", sum(1 for row in rows if row.get("事件等级") in {"A", "S", "高"}), "按事件等级统计"),
            ("已复盘关联", len(reviewed_event_ids), "来自 Prediction Ledger 状态"),
            ("数据来源", page_data.source_label, "本地只读"),
        ],
    )

    cols = st.columns([1, 1.7, 1.2, 1.2])
    level = cols[0].selectbox("事件等级", ["全部", "A", "B", "C"], index=0)
    query = cols[1].text_input("文本搜索", "")
    stage = cols[2].selectbox("生命周期状态", ["全部", "new", "developing", "confirmed", "analysis_only", "stale", "closed"], index=0)
    source_filter = cols[3].selectbox("数据来源", ["全部", "real", "demo", "placeholder"], index=0)
    if level != "全部":
        rows = [row for row in rows if row.get("事件等级") == level]
    if stage != "全部":
        lifecycle_by_title = {row.get("标题"): row.get("阶段") for row in page_data.lifecycle_events + page_data.background_events}
        rows = [row for row in rows if lifecycle_by_title.get(row.get("标题")) == stage]
    if source_filter != "全部":
        rows = [row for row in rows if row.get("source_kind") == source_filter]
    if query:
        needle = query.casefold()
        rows = [row for row in rows if needle in str(row).casefold()]

    if not rows:
        _render_empty_state_html(st, "暂无事件卡片，请先运行 demo 或新闻扫描。")
        return
    st.markdown(_event_cards_html(rows, page_data), unsafe_allow_html=True)
    for row in rows[:10]:
        with st.expander(f"展开详情：{row.get('标题') or '--'}"):
            st.write("因果链摘要：")
            st.write(row.get("因果链摘要") or ["--"])
            evidence_rows = _evidence_rows_for_event(page_data, row)
            st.write("因果证据层：")
            if evidence_rows:
                st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
            else:
                st.write("暂无因果证据层记录，请生成 EventCard 或运行 demo。")
            st.write("风险因素：")
            st.write(row.get("风险因素") or ["--"])
            st.write("后续验证指标：")
            st.write(row.get("后续验证指标") or ["--"])
            st.write(f"历史验证：{row.get('历史验证') or '--'}")

    with st.expander("查看 raw EventCard 表格"):
        _render_table_or_empty(st, rows, "暂无 EventCard。")
    _render_risk_notice(st)


def render_prediction_ledger(st: Any, page_data: EventConsoleData) -> None:
    """Render Prediction Ledger rows from local SQLite/demo SQLite."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "预测账本",
        "记录系统已发布的市场判断，包括事件、资产、方向、时间窗口、置信度和复盘状态。",
        page_data,
        badges=["Prediction Ledger"],
    )
    rows = page_data.prediction_ledger_rows
    _render_summary_cards(
        st,
        [
            ("预测记录数", len(rows), "Prediction Ledger"),
            ("涉及事件数", len({row.get("事件ID") or row.get("事件") for row in rows}), "去重统计"),
            ("涉及资产数", len({row.get("资产") for row in rows if row.get("资产") not in {None, '未记录'}}), "predicted_assets"),
            ("Active", sum(1 for row in rows if str(row.get("状态")).casefold() in {"active", "tracking", "open"}), "按状态字段"),
            ("已复盘", sum(1 for row in rows if str(row.get("状态")).casefold() in {"reviewed", "closed", "completed"}), "按状态字段"),
        ],
    )
    cols = st.columns([1.8, 1.2, 1.1, 1.2, 1.2, 1.2])
    query = cols[0].text_input("文本搜索", "", placeholder="搜索事件、资产、PredictionID")
    event_type = cols[1].selectbox("事件类型", _options_from_rows(rows, "事件类型"), index=0)
    direction = cols[2].selectbox("方向", _options_from_rows(rows, "方向"), index=0)
    window = cols[3].selectbox("时间窗口", _options_from_rows(rows, "时间窗口"), index=0)
    status = cols[4].selectbox("状态", _options_from_rows(rows, "状态"), index=0)
    asset_type = cols[5].selectbox("资产类型", _options_from_rows(rows, "资产类型"), index=0)
    if query:
        needle = query.casefold()
        rows = [row for row in rows if needle in str(row).casefold()]
    rows = _filter_exact(rows, "事件类型", event_type)
    rows = _filter_exact(rows, "方向", direction)
    rows = _filter_exact(rows, "时间窗口", window)
    rows = _filter_exact(rows, "状态", status)
    rows = _filter_exact(rows, "资产类型", asset_type)
    if not rows:
        _render_empty_state_html(st, "暂无预测记录，请先运行事件分析流程。")
        return
    st.markdown(_ledger_page_html(rows), unsafe_allow_html=True)
    with st.expander("查看 raw Prediction Ledger 表格"):
        _render_table_or_empty(st, rows, "暂无预测记录，请先运行事件分析流程。")
    _render_risk_notice(st)


def render_lifecycle(st: Any, page_data: EventConsoleData) -> None:
    """Render lifecycle events."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "事件生命周期",
        "跟踪事件从发现、验证、分析、发布、跟踪到复盘归档的状态演化。",
        page_data,
        badges=[_source_label(page_data.lifecycle_summary)],
    )
    foreground = page_data.lifecycle_events
    background = page_data.background_events
    rows = foreground + background
    _render_summary_cards(
        st,
        [
            ("跟踪事件数", len(rows), "Lifecycle Store"),
            ("正在跟踪", sum(1 for row in rows if row.get("阶段") in {"new", "developing", "confirmed"}), "按 lifecycle_stage"),
            ("已复盘", "--", "当前 schema 未记录"),
            ("已关闭/归档", sum(1 for row in rows if row.get("阶段") in {"stale", "closed", "resolved"}), "按 lifecycle_stage"),
            ("最近更新时间", _latest_from_rows(rows, "最近出现"), "last_seen_at"),
        ],
    )
    stage = st.selectbox("阶段过滤", ["全部", "developing", "analysis_only", "stale", "closed", "new", "confirmed"], index=0)
    if stage != "全部":
        rows = [row for row in rows if row.get("阶段") == stage]

    if not rows:
        _render_empty_state_html(st, "暂无生命周期记录，请运行 lifecycle tracker。")
        return
    st.markdown(_lifecycle_page_html(rows), unsafe_allow_html=True)
    with st.expander("查看 raw lifecycle 表格"):
        _render_table_or_empty(st, rows, "暂无生命周期记录，请运行 lifecycle tracker。")


def render_reviews(st: Any, page_data: EventConsoleData) -> None:
    """Render review results."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "自动复盘结果",
        "展示系统对历史预测在 T+1 / T+3 / T+7 等窗口的方向、超额收益和因果有效性验证。",
        page_data,
        badges=["ReviewResult"],
    )
    summary = page_data.review_summary
    _render_summary_cards(
        st,
        [
            ("复盘结果数", summary.get("复盘结果数", 0), "ReviewResult"),
            ("因果链支持", summary.get("valid", 0), "causal_validity=valid"),
            ("未验证", summary.get("invalid", 0), "causal_validity=invalid"),
            ("观察/未知", summary.get("unknown", 0), "causal_validity=unknown"),
            ("平均超额收益", format_return_pct(summary.get("平均超额收益"), signed=True), "真实 ReviewResult 均值"),
        ],
    )
    rows = page_data.review_results
    cols = st.columns([1.2, 1.2, 1.2, 1.5, 1.8])
    validity = cols[0].selectbox("因果有效性", ["全部", "valid", "invalid", "unknown"], index=0)
    direction = cols[1].selectbox("方向判断", _options_from_rows(rows, "方向结果"), index=0)
    window = cols[2].selectbox("时间窗口", _options_from_rows(rows, "窗口"), index=0)
    asset = cols[3].selectbox("资产", _options_from_rows(rows, "资产"), index=0)
    query = cols[4].text_input("文本搜索", "")
    if validity != "全部":
        rows = [row for row in rows if row.get("因果有效性") == validity]
    rows = _filter_exact(rows, "方向结果", direction)
    rows = _filter_exact(rows, "窗口", window)
    rows = _filter_exact(rows, "资产", asset)
    if query:
        needle = query.casefold()
        rows = [row for row in rows if needle in str(row).casefold()]
    if not rows:
        _render_empty_state_html(st, "暂无自动复盘结果，请运行 auto_review_runner。")
        return
    st.markdown(_reviews_page_html(rows), unsafe_allow_html=True)
    with st.expander("查看 raw ReviewResult 表格"):
        _render_table_or_empty(st, rows, "暂无自动复盘结果，请运行 auto_review_runner。")
    _render_risk_notice(st)


def render_rule_updates(st: Any, page_data: EventConsoleData) -> None:
    """Render aggregated rule updates."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "规则更新",
        "根据自动复盘结果，对因果规则、资产映射和风险提示进行结构化修正。",
        page_data,
        badges=["RuleUpdate"],
    )
    rows = page_data.rule_updates
    _render_summary_cards(
        st,
        [
            ("规则更新数", len(rows), "RuleUpdate"),
            ("权重上调", sum(1 for row in rows if row.get("动作") in {"strengthen", "slightly_strengthen"}), "按动作字段"),
            ("权重下调", sum(1 for row in rows if row.get("动作") == "weaken"), "按动作字段"),
            ("新增/未知", sum(1 for row in rows if row.get("动作") not in {"strengthen", "slightly_strengthen", "weaken", "unchanged"}), "schema 未细分新增"),
            ("最近更新时间", _latest_from_rows(rows, "创建时间"), "created_at"),
        ],
    )
    action = st.selectbox("动作过滤", ["全部", "strengthen", "weaken", "slightly_strengthen", "unchanged"], index=0)
    if action != "全部":
        rows = [row for row in rows if row.get("动作") == action]
    if not rows:
        _render_empty_state_html(st, "暂无规则更新，等待复盘后生成。")
        return
    st.markdown(_rule_feedback_panel_html(page_data), unsafe_allow_html=True)
    st.markdown(_rule_updates_page_html(rows), unsafe_allow_html=True)
    with st.expander("查看 raw RuleUpdate 表格"):
        _render_table_or_empty(st, rows, "暂无规则更新，等待复盘后生成。")


def render_scheduler_status(st: Any, page_data: EventConsoleData) -> None:
    """Render scheduler status in a presentation-friendly way."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "调度器状态",
        "展示本地调度任务、运行日志、数据源状态和最近一次任务结果。",
        page_data,
        badges=["scheduler_state.json", "scheduler_runs.jsonl"],
    )
    status_counts = page_data.scheduler_status_counts
    latest_run = page_data.scheduler_runs[0].get("开始时间") if page_data.scheduler_runs else "未运行"
    _render_summary_cards(
        st,
        [
            ("最近运行时间", latest_run, "scheduler_runs.jsonl"),
            ("成功任务数", status_counts.get("success", 0), "status=success"),
            ("失败任务数", status_counts.get("failed", 0), "status=failed"),
            ("未运行任务数", sum(1 for row in page_data.scheduler_status_rows if row.get("状态") == "未运行"), "任务状态"),
            ("当前模式", "Demo" if page_data.source_kind == "demo" else "Normal", page_data.source_label),
        ],
    )

    if page_data.friendly_scheduler_warnings:
        _render_info_note(st, "调度提示", "；".join(page_data.friendly_scheduler_warnings))
        with st.expander("展开查看详细 warning"):
            st.write(page_data.scheduler_warnings)

    st.markdown(_scheduler_page_html(page_data), unsafe_allow_html=True)

    with st.expander("Configured Jobs"):
        _render_table_or_empty(st, page_data.scheduler_jobs, "暂无 scheduler config。")
    with st.expander("Tracking Policies"):
        _render_table_or_empty(st, page_data.tracking_policies, "暂无 tracking policies。")
    with st.expander("Recent Runs"):
        _render_table_or_empty(st, page_data.scheduler_runs, "暂无调度运行记录。")
    with st.expander("开发者调试信息"):
        st.json(page_data.raw_debug)


def render_historical_cases(st: Any, page_data: EventConsoleData) -> None:
    """Render the historical case store."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "历史案例",
        "沉淀同类事件的历史市场表现，用于辅助当前因果链验证和风险提示。",
        page_data,
        badges=["Historical Case Store"],
    )
    rows = page_data.historical_cases
    summary = page_data.historical_case_summary
    _render_summary_cards(
        st,
        [
            ("历史案例数", summary.get("历史案例数", 0), "HistoricalCaseStore"),
            ("事件类型数", summary.get("事件类型数", 0), "event_type"),
            ("已有 outcome", summary.get("已有 outcome", 0), "outcome"),
            ("可验证案例", summary.get("可验证案例", 0), "causal_assessment"),
        ],
    )
    cols = st.columns([2, 1.4])
    query = cols[0].text_input("文本搜索", "")
    event_type = cols[1].selectbox("事件类型", _options_from_rows(rows, "事件类型"), index=0)
    rows = _filter_exact(rows, "事件类型", event_type)
    if query:
        needle = query.casefold()
        rows = [row for row in rows if needle in str(row).casefold()]
    if not rows:
        _render_empty_state_html(st, "暂无历史案例，请初始化 Historical Case Store。")
        return
    st.markdown(_historical_cases_html(rows), unsafe_allow_html=True)
    with st.expander("查看 raw HistoricalCase 表格"):
        _render_table_or_empty(st, rows, "暂无历史案例，请初始化 Historical Case Store。")
    _render_risk_notice(st)


def render_system_status(st: Any, page_data: EventConsoleData) -> None:
    """Render read-only productized system status."""
    st.markdown(_dashboard_css(), unsafe_allow_html=True)
    _render_product_header(
        st,
        "系统状态",
        "展示本地数据路径、运行模式、报告、账本、生命周期和调度状态。",
        page_data,
        badges=[page_data.source_label],
    )
    status = page_data.data_status or {}
    _render_summary_cards(
        st,
        [
            ("运行模式", "Demo" if page_data.source_kind == "demo" else "Normal", page_data.source_label),
            ("本地报告", status.get("reports_count", 0), "reports"),
            ("Ledger", "已连接" if status.get("ledger_exists") else "未发现", "SQLite"),
            ("Lifecycle", "已连接" if status.get("lifecycle_store_exists") else "未发现", "JSON Store"),
            ("Scheduler Runs", "已连接" if status.get("scheduler_runs_exists") else "未发现", "JSONL"),
        ],
    )
    st.markdown(_system_status_html(page_data), unsafe_allow_html=True)
    with st.expander("查看系统 raw debug"):
        st.json(page_data.raw_debug)


def render_footer(st: Any) -> None:
    """Render compliance footer."""
    st.divider()
    st.caption(RISK_DISCLAIMER)


def _dashboard_css() -> str:
    """Return page-level CSS for the dashboard."""
    return """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div.block-container {
    max-width: 100% !important;
    padding: 0.75rem 1.25rem 1.25rem 1.25rem !important;
}
.stApp {
    background:
        radial-gradient(circle at top left, rgba(46, 111, 255, 0.08), transparent 28rem),
        linear-gradient(180deg, #f7faff 0%, #f3f7fd 100%);
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #061d49 0%, #041633 58%, #031126 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    min-width: 232px !important;
    max-width: 240px !important;
}
section[data-testid="stSidebar"] * {
    color: #edf5ff !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    border-radius: 9px;
    padding: 0.65rem 0.75rem;
    margin: 0.1rem 0;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: linear-gradient(90deg, #0b77ff, #0064f0);
    box-shadow: 0 10px 24px rgba(0, 96, 240, 0.32);
}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: rgba(237, 245, 255, 0.68) !important;
}
.ea-shell {
    color: #0b1748;
    font-family: "Inter", "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
}
.ea-grid {
    display: grid;
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap: 12px;
}
.ea-card {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #dbe6f6;
    border-radius: 8px;
    box-shadow: 0 10px 24px rgba(15, 44, 88, 0.055);
    overflow: hidden;
}
.ea-hero {
    grid-column: span 5;
    min-height: 148px;
    padding: 22px 22px 18px;
    background:
        radial-gradient(circle at 78% 50%, rgba(46, 132, 255, 0.16), transparent 11rem),
        linear-gradient(105deg, #ffffff 0%, #f4f9ff 62%, #e9f3ff 100%);
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 10px;
}
.ea-hero h1 {
    margin: 0 0 12px;
    font-size: 25px;
    line-height: 1.15;
    letter-spacing: 0;
}
.ea-hero p {
    margin: 0 0 16px;
    color: #4b5d83;
    font-weight: 600;
    line-height: 1.55;
}
.ea-primary-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    height: 36px;
    padding: 0 18px;
    border-radius: 6px;
    background: linear-gradient(90deg, #0878ff, #005ee8);
    color: #fff;
    font-weight: 800;
    box-shadow: 0 10px 22px rgba(0, 98, 232, 0.24);
}
.ea-hero-art {
    position: relative;
    min-height: 120px;
}
.ea-platform {
    position: absolute;
    inset: 16px 8px 8px 6px;
    border-radius: 50%;
    background:
        radial-gradient(circle, #ffffff 0 18%, #dcecff 19% 34%, transparent 35%),
        repeating-radial-gradient(circle, rgba(45, 126, 255, 0.28) 0 2px, transparent 3px 17px);
    transform: perspective(260px) rotateX(62deg);
    border: 1px solid rgba(76, 139, 235, 0.28);
}
.ea-magnifier {
    position: absolute;
    right: 24px;
    bottom: 20px;
    width: 54px;
    height: 54px;
    border-radius: 50%;
    border: 8px solid rgba(37, 116, 255, 0.78);
    box-shadow: inset 0 0 0 7px rgba(255,255,255,0.7), 0 12px 28px rgba(0, 88, 222, 0.24);
}
.ea-magnifier::after {
    content: "";
    position: absolute;
    width: 42px;
    height: 8px;
    border-radius: 8px;
    background: rgba(37, 116, 255, 0.78);
    right: -34px;
    bottom: -18px;
    transform: rotate(45deg);
}
.ea-linechart {
    position: absolute;
    right: 12px;
    top: 22px;
    width: 120px;
    height: 66px;
    border-left: 2px solid #bcd3f6;
    border-bottom: 2px solid #bcd3f6;
    background:
        linear-gradient(135deg, transparent 12%, #1971ff 13% 15%, transparent 16% 36%, #1971ff 37% 39%, transparent 40% 60%, #1971ff 61% 63%, transparent 64%),
        linear-gradient(180deg, transparent 0 70%, rgba(31, 118, 255, 0.08) 71% 100%);
}
.ea-metric {
    grid-column: span 1;
    min-height: 148px;
    padding: 16px 14px 12px;
}
.ea-metric-title {
    color: #26376b;
    font-size: 13px;
    font-weight: 800;
    margin-bottom: 8px;
}
.ea-metric-number {
    font-size: 28px;
    font-weight: 900;
    color: #06184b;
    margin-bottom: 4px;
}
.ea-metric-number span {
    font-size: 15px;
    margin-left: 3px;
}
.ea-delta {
    font-size: 12px;
    color: #69789d;
    margin-bottom: 12px;
}
.ea-delta .up { color: #ff3248; font-weight: 800; }
.ea-delta .down { color: #00a889; font-weight: 800; }
.ea-spark {
    height: 34px;
    border-radius: 4px;
    background:
        linear-gradient(135deg, transparent 9%, var(--spark) 10% 12%, transparent 13% 28%, var(--spark) 29% 31%, transparent 32% 44%, var(--spark) 45% 47%, transparent 48% 66%, var(--spark) 67% 69%, transparent 70%),
        linear-gradient(180deg, rgba(255,255,255,0), rgba(39,120,255,0.08));
}
.ea-section {
    padding: 12px 14px;
}
.ea-section-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}
.ea-section-title h2 {
    font-size: 16px;
    margin: 0;
    letter-spacing: 0;
}
.ea-link {
    color: #1270ff;
    font-size: 12px;
    font-weight: 800;
}
.ea-top-events {
    grid-column: span 7;
}
.ea-asset-watch {
    grid-column: span 5;
}
.ea-event-cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
}
.ea-event-card {
    border: 1px solid #dce6f4;
    border-radius: 7px;
    padding: 10px;
    min-height: 142px;
    position: relative;
}
.ea-rank {
    position: absolute;
    left: -7px;
    top: -7px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    color: #fff;
    font-size: 12px;
    font-weight: 900;
    background: #ff3b36;
    border: 2px solid #fff;
}
.ea-event-head {
    display: grid;
    grid-template-columns: 56px 1fr auto;
    gap: 8px;
    align-items: start;
}
.ea-thumb {
    height: 46px;
    border-radius: 6px;
    background: linear-gradient(135deg, #12336f, #36a3ff);
    display: grid;
    place-items: center;
    color: #fff;
    font-weight: 900;
}
.ea-event-title {
    font-size: 14px;
    font-weight: 900;
    color: #0a1a50;
    line-height: 1.3;
}
.ea-tag {
    display: inline-flex;
    align-items: center;
    height: 22px;
    padding: 0 8px;
    border-radius: 5px;
    color: #0b70f0;
    background: #eaf3ff;
    font-size: 11px;
    font-weight: 800;
    white-space: nowrap;
}
.ea-stars {
    color: #f83347;
    font-size: 11px;
    font-weight: 900;
}
.ea-confidence {
    color: #00a989;
    font-weight: 900;
    font-size: 13px;
    text-align: right;
}
.ea-caption {
    color: #53668e;
    font-size: 12px;
    line-height: 1.45;
}
.ea-mini-list {
    margin: 7px 0 0;
    padding-left: 16px;
    color: #253866;
    font-size: 12px;
    line-height: 1.45;
}
.ea-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.ea-table th {
    text-align: left;
    color: #52658f;
    font-size: 11px;
    padding: 7px 6px;
    border-bottom: 1px solid #dce6f4;
}
.ea-table td {
    padding: 8px 6px;
    border-bottom: 1px solid #edf2fa;
    color: #1f315d;
    vertical-align: middle;
}
.ea-asset-icon {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: inline-grid;
    place-items: center;
    margin-right: 8px;
    color: #fff;
    background: #2b76ff;
    font-size: 11px;
    font-weight: 900;
}
.ea-trend {
    display: inline-block;
    width: 72px;
    height: 22px;
    background:
        linear-gradient(135deg, transparent 18%, currentColor 19% 21%, transparent 22% 45%, currentColor 46% 48%, transparent 49% 72%, currentColor 73% 75%, transparent 76%);
}
.ea-causal {
    grid-column: span 5;
}
.ea-ledger {
    grid-column: span 7;
}
.ea-chain {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    align-items: center;
    gap: 14px;
}
.ea-node {
    border: 1px solid #dce6f4;
    border-radius: 7px;
    min-height: 78px;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 10px;
    color: #253866;
    font-weight: 800;
    background: linear-gradient(180deg, #fff, #f7fbff);
}
.ea-node-icon {
    color: #0878ff;
    font-size: 22px;
    line-height: 1;
    margin-bottom: 6px;
}
.ea-progress {
    height: 5px;
    border-radius: 999px;
    background: #e3ebf7;
    overflow: hidden;
}
.ea-progress span {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: #18b985;
}
.ea-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 48px;
    height: 22px;
    border-radius: 999px;
    background: #eaf3ff;
    color: #116fe8;
    font-size: 11px;
    font-weight: 800;
}
.ea-lifecycle {
    grid-column: span 5;
}
.ea-review {
    grid-column: span 7;
}
.ea-timeline {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 8px;
    align-items: center;
}
.ea-stage {
    text-align: center;
    color: #53668e;
    font-size: 12px;
    font-weight: 800;
}
.ea-stage-dot {
    width: 30px;
    height: 30px;
    margin: 0 auto 6px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: #dfeaff;
    color: #3467b3;
}
.ea-stage.active .ea-stage-dot {
    background: #0b75ff;
    color: #fff;
    box-shadow: 0 0 0 8px #e9f2ff;
}
.ea-rule {
    grid-column: span 5;
}
.ea-status {
    grid-column: span 3;
}
.ea-scheduler {
    grid-column: span 4;
}
.ea-rule-row {
    display: grid;
    grid-template-columns: 58px 1fr auto;
    gap: 10px;
    align-items: center;
    padding: 5px 0;
    color: #253866;
    font-size: 12px;
}
.ea-time-small {
    color: #52658f;
    font-weight: 800;
}
.ea-dot-line {
    border-left: 2px solid #2078ff;
    height: 18px;
    margin-left: 4px;
}
.ea-status-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}
.ea-status-item {
    display: grid;
    gap: 3px;
    color: #53668e;
    font-size: 12px;
}
.ea-status-number {
    color: #06184b;
    font-size: 20px;
    font-weight: 900;
}
.ea-health-list {
    display: grid;
    gap: 6px;
    font-size: 12px;
    color: #253866;
}
.ea-health-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
}
.ea-ok {
    color: #00a878;
    font-weight: 900;
}
.ea-source-chip {
    display: inline-flex;
    align-items: center;
    height: 20px;
    padding: 0 7px;
    border-radius: 999px;
    background: #eaf3ff;
    color: #126ee8;
    font-size: 10px;
    font-weight: 900;
    white-space: nowrap;
}
.ea-source-chip.demo {
    background: #fff4df;
    color: #b86400;
}
.ea-source-chip.placeholder {
    background: #f0f2f6;
    color: #66718f;
}
.ea-empty {
    border: 1px dashed #cbd8ea;
    border-radius: 7px;
    padding: 14px;
    color: #53668e;
    font-size: 13px;
    background: #f8fbff;
}
.ea-subtitle {
    color: #69789d;
    font-size: 11px;
    font-weight: 800;
    margin-left: 8px;
}
.ea-briefing-preview {
    margin-top: 8px;
    color: #53668e;
    font-size: 12px;
    line-height: 1.45;
}
@media (max-width: 1180px) {
    .ea-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .ea-hero, .ea-top-events, .ea-asset-watch, .ea-causal, .ea-ledger, .ea-lifecycle, .ea-review, .ea-rule, .ea-status, .ea-scheduler {
        grid-column: span 6;
    }
    .ea-metric { grid-column: span 2; }
    .ea-event-cards { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
    .ea-grid { grid-template-columns: 1fr; }
    .ea-hero, .ea-metric, .ea-top-events, .ea-asset-watch, .ea-causal, .ea-ledger, .ea-lifecycle, .ea-review, .ea-rule, .ea-status, .ea-scheduler {
        grid-column: span 1;
    }
    .ea-hero { grid-template-columns: 1fr; }
    .ea-chain, .ea-timeline, .ea-status-grid { grid-template-columns: 1fr; }
}
.ea-shell {
    max-width: 1480px;
    margin: 0 auto;
}
.ea-grid {
    gap: 14px;
}
.ea-card {
    border-color: #dce7f7;
    border-radius: 8px;
    box-shadow: 0 14px 34px rgba(23, 50, 91, 0.075);
}
.ea-section {
    padding: 16px;
}
.ea-section-title {
    min-height: 28px;
    gap: 12px;
}
.ea-section-title h2 {
    font-size: 15px;
    line-height: 1.35;
    color: #071944;
}
.ea-section-link,
.ea-link {
    color: #126be8;
    font-size: 12px;
    font-weight: 900;
    text-decoration: none;
    white-space: nowrap;
}
.ea-section-link:hover,
.ea-link:hover {
    color: #064db8;
    text-decoration: underline;
}
.ea-hero {
    grid-column: span 7;
    min-height: 152px;
    padding: 22px;
    align-items: center;
    background:
        radial-gradient(circle at 82% 46%, rgba(56, 147, 255, 0.18), transparent 11rem),
        linear-gradient(116deg, #ffffff 0%, #f6fbff 58%, #e7f3ff 100%);
}
.ea-hero h1 {
    font-size: 28px;
    margin-bottom: 10px;
}
.ea-hero p {
    max-width: 620px;
    margin-bottom: 12px;
    color: #425678;
    font-size: 14px;
}
.ea-primary-btn {
    height: 34px;
    border-radius: 7px;
    text-decoration: none;
}
.ea-briefing-card {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 8px 10px;
    align-items: center;
    margin-top: 10px;
    padding: 9px 10px;
    border: 1px solid #dbe8f8;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.78);
    color: #415575;
    font-size: 12px;
    line-height: 1.35;
}
.ea-briefing-main {
    font-weight: 900;
    color: #10204d;
}
.ea-hero-art {
    min-height: 132px;
    border-radius: 8px;
    background: linear-gradient(145deg, rgba(226, 241, 255, 0.78), rgba(255, 255, 255, 0.22));
}
.ea-radar {
    position: absolute;
    inset: 14px 20px 8px 14px;
    border-radius: 50%;
    background:
        radial-gradient(circle at 50% 50%, rgba(255,255,255,0.95) 0 10%, rgba(169, 213, 255, 0.42) 11% 12%, transparent 13% 28%, rgba(81, 154, 255, 0.28) 29% 30%, transparent 31% 47%, rgba(81, 154, 255, 0.20) 48% 49%, transparent 50%),
        conic-gradient(from 318deg, rgba(0, 108, 255, 0.28), rgba(0, 108, 255, 0.02) 34%, transparent 36%);
    border: 1px solid rgba(60, 139, 246, 0.18);
    transform: perspective(300px) rotateX(57deg);
}
.ea-arrow {
    position: absolute;
    right: 20px;
    top: 24px;
    width: 102px;
    height: 52px;
    border-left: 2px solid #b8d4fb;
    border-bottom: 2px solid #b8d4fb;
    background:
        linear-gradient(135deg, transparent 11%, #1674ff 12% 15%, transparent 16% 36%, #1674ff 37% 40%, transparent 41% 62%, #1674ff 63% 66%, transparent 67%);
}
.ea-arrow::after {
    content: "";
    position: absolute;
    right: -2px;
    top: -2px;
    border-left: 10px solid #1674ff;
    border-top: 6px solid transparent;
    border-bottom: 6px solid transparent;
    transform: rotate(-22deg);
}
.ea-magnifier {
    right: 30px;
    bottom: 22px;
    width: 48px;
    height: 48px;
    border-width: 7px;
}
.ea-metric {
    min-height: 138px;
    padding: 15px 13px 12px;
    display: flex;
    flex-direction: column;
}
.ea-metric-title {
    min-height: 30px;
    margin-bottom: 8px;
    color: #31436a;
}
.ea-metric-number {
    min-height: 35px;
    font-size: 26px;
    line-height: 1.05;
    overflow-wrap: anywhere;
}
.ea-health-main {
    font-size: 21px;
    font-weight: 950;
    color: #06184b;
    line-height: 1.18;
    min-height: 31px;
}
.ea-health-row-inline {
    display: flex;
    align-items: center;
    gap: 7px;
    margin: 4px 0 6px;
}
.ea-health-badge {
    display: inline-flex;
    align-items: center;
    height: 22px;
    padding: 0 9px;
    border-radius: 999px;
    background: #e5f8f1;
    color: #07815d;
    font-size: 11px;
    font-weight: 900;
}
.ea-spark {
    margin-top: auto;
    height: 28px;
    opacity: 0.95;
}
.ea-top-events {
    grid-column: span 7;
}
.ea-asset-watch {
    grid-column: span 5;
}
.ea-event-cards {
    gap: 12px;
}
.ea-event-cards.cols-1 {
    grid-template-columns: 1fr;
}
.ea-event-cards.cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}
.ea-event-cards.cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}
.ea-event-card {
    border-color: #dce8f8;
    border-radius: 8px;
    padding: 14px;
    min-height: 176px;
    background: linear-gradient(180deg, #ffffff 0%, #f9fcff 100%);
}
.ea-event-card.wide {
    min-height: 160px;
}
.ea-event-head {
    grid-template-columns: 44px 1fr auto;
    gap: 10px;
}
.ea-thumb {
    height: 42px;
    border-radius: 8px;
}
.ea-event-title {
    font-size: 14px;
}
.ea-event-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    margin-top: 8px;
}
.ea-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
}
.ea-chip {
    display: inline-flex;
    align-items: center;
    min-height: 22px;
    padding: 0 8px;
    border-radius: 999px;
    background: #eef5ff;
    color: #145cc3;
    font-size: 11px;
    font-weight: 900;
}
.ea-chip.neutral {
    color: #52617d;
    background: #f2f5f9;
}
.ea-chip.signal {
    color: #075d86;
    background: #e9f8ff;
}
.ea-mini-list {
    margin-top: 9px;
}
.ea-mini-list li {
    margin: 2px 0;
}
.ea-table {
    border-collapse: separate;
    border-spacing: 0;
    font-size: 12px;
}
.ea-table th {
    background: #f6f9fe;
    border-top: 1px solid #edf3fb;
    border-bottom: 1px solid #dfe9f7;
    color: #5d6f91;
    padding: 9px 8px;
}
.ea-table td {
    border-bottom: 1px solid #eef3fa;
    padding: 9px 8px;
}
.ea-table tr:last-child td {
    border-bottom: 0;
}
.ea-asset-cell {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 900;
    color: #0e2251;
}
.ea-asset-icon {
    margin-right: 0;
    background: linear-gradient(135deg, #0c67db, #38a7ff);
}
.ea-causal {
    grid-column: span 5;
}
.ea-ledger {
    grid-column: span 7;
}
.ea-chain {
    position: relative;
    gap: 12px;
}
.ea-node {
    min-height: 92px;
    border-radius: 8px;
    background: linear-gradient(180deg, #ffffff, #f6fbff);
}
.ea-node-icon {
    font-size: 12px;
    font-weight: 950;
    color: #126be8;
}
.ea-node-title {
    color: #62718f;
    font-size: 11px;
    font-weight: 900;
    margin-bottom: 4px;
}
.ea-node-label {
    color: #11224f;
    font-size: 13px;
    line-height: 1.35;
    font-weight: 900;
}
.ea-lifecycle {
    grid-column: span 5;
}
.ea-review {
    grid-column: span 7;
}
.ea-timeline {
    gap: 0;
    padding: 6px 0 4px;
}
.ea-stage {
    position: relative;
    color: #53668e;
}
.ea-stage:not(:last-child)::after {
    content: "";
    position: absolute;
    top: 15px;
    left: calc(50% + 18px);
    width: calc(100% - 36px);
    height: 2px;
    background: #dbe7f6;
}
.ea-stage-dot {
    position: relative;
    z-index: 1;
}
.ea-rule {
    grid-column: span 5;
}
.ea-rule-list {
    display: grid;
    gap: 9px;
}
.ea-rule-row {
    grid-template-columns: 76px 1fr auto;
    border-left: 3px solid #2b78ff;
    background: #f8fbff;
    border-radius: 8px;
    padding: 9px 10px;
}
.ea-status {
    grid-column: span 3;
}
.ea-scheduler {
    grid-column: span 4;
}
.ea-status-grid {
    gap: 10px;
}
.ea-status-item {
    border: 1px solid #e3ecf8;
    border-radius: 8px;
    padding: 10px;
    background: #f8fbff;
}
.ea-health-list {
    gap: 8px;
}
.ea-health-row {
    align-items: center;
    padding: 9px 10px;
    border: 1px solid #e3ecf8;
    border-radius: 8px;
    background: #f8fbff;
}
.ea-source-chip {
    max-width: 100%;
}
.ea-empty {
    border-radius: 8px;
    padding: 16px;
    background: #f8fbff;
    color: #52627f;
}
@media (max-width: 1180px) {
    .ea-hero, .ea-top-events, .ea-asset-watch, .ea-causal, .ea-ledger, .ea-lifecycle, .ea-review, .ea-rule, .ea-status, .ea-scheduler {
        grid-column: span 6;
    }
    .ea-event-cards.cols-2, .ea-event-cards.cols-3 { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
    .ea-hero, .ea-metric, .ea-top-events, .ea-asset-watch, .ea-causal, .ea-ledger, .ea-lifecycle, .ea-review, .ea-rule, .ea-status, .ea-scheduler {
        grid-column: span 1;
    }
    .ea-event-cards.cols-1, .ea-event-cards.cols-2, .ea-event-cards.cols-3,
    .ea-chain, .ea-timeline, .ea-status-grid {
        grid-template-columns: 1fr;
    }
    .ea-stage:not(:last-child)::after { display: none; }
}
.ea-page-shell {
    max-width: 1480px;
    margin: 0 auto;
    color: #0b1748;
    font-family: "Inter", "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
}
.ea-page-header {
    margin: 0 0 14px;
    padding: 20px 22px;
    border: 1px solid #dce7f7;
    border-radius: 8px;
    background:
        radial-gradient(circle at right top, rgba(47, 128, 255, 0.14), transparent 16rem),
        linear-gradient(116deg, rgba(255,255,255,0.96), rgba(245,250,255,0.96));
    box-shadow: 0 14px 34px rgba(23, 50, 91, 0.075);
}
.ea-page-kicker {
    color: #126be8;
    font-size: 12px;
    font-weight: 950;
    letter-spacing: 0;
    margin-bottom: 8px;
}
.ea-page-header h1 {
    margin: 0;
    font-size: 26px;
    line-height: 1.18;
    letter-spacing: 0;
    color: #071944;
}
.ea-page-subtitle {
    margin: 9px 0 0;
    color: #425678;
    font-size: 14px;
    line-height: 1.55;
    font-weight: 600;
}
.ea-page-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin-top: 13px;
}
.ea-summary-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 12px;
    margin: 0 0 14px;
}
.ea-summary-card {
    min-height: 100px;
    padding: 14px;
    border: 1px solid #dce7f7;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.95);
    box-shadow: 0 12px 28px rgba(23, 50, 91, 0.06);
}
.ea-summary-title {
    color: #31436a;
    font-size: 12px;
    font-weight: 900;
}
.ea-summary-value {
    margin-top: 9px;
    color: #071944;
    font-size: 24px;
    line-height: 1.12;
    font-weight: 950;
    overflow-wrap: anywhere;
}
.ea-summary-note {
    margin-top: 9px;
    color: #69789d;
    font-size: 11px;
    font-weight: 800;
}
.ea-page-stack {
    display: grid;
    gap: 12px;
}
.ea-wide-card,
.ea-product-card,
.ea-briefing-section,
.ea-warning-card,
.ea-task-card,
.ea-system-item,
.ea-timeline-card {
    border: 1px solid #dce7f7;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.95);
    box-shadow: 0 12px 28px rgba(23, 50, 91, 0.06);
}
.ea-wide-card {
    padding: 16px;
}
.ea-card-list {
    display: grid;
    gap: 12px;
}
.ea-product-card,
.ea-briefing-section,
.ea-warning-card,
.ea-task-card,
.ea-system-item,
.ea-timeline-card {
    padding: 15px;
}
.ea-card-title-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: 10px;
}
.ea-card-title {
    color: #071944;
    font-size: 15px;
    font-weight: 950;
    line-height: 1.35;
}
.ea-detail-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
}
.ea-detail-item {
    padding: 10px;
    border: 1px solid #e3ecf8;
    border-radius: 8px;
    background: #f8fbff;
}
.ea-detail-label {
    color: #687896;
    font-size: 11px;
    font-weight: 900;
    margin-bottom: 5px;
}
.ea-detail-value {
    color: #11224f;
    font-size: 13px;
    font-weight: 850;
    line-height: 1.35;
}
.ea-warning-card {
    background: #fffaf0;
    border-color: #f3dfb8;
}
.ea-briefing-section h3 {
    margin: 0 0 10px;
    color: #071944;
    font-size: 16px;
    letter-spacing: 0;
}
.ea-briefing-section ul,
.ea-product-card ul,
.ea-history-card ul {
    margin: 8px 0 0;
    padding-left: 18px;
    color: #253866;
    line-height: 1.55;
    font-size: 13px;
}
.ea-ledger-list,
.ea-review-list,
.ea-history-list,
.ea-task-list,
.ea-system-grid {
    display: grid;
    gap: 12px;
}
.ea-ledger-row {
    display: grid;
    grid-template-columns: minmax(180px, 1.4fr) minmax(120px, 0.8fr) repeat(4, minmax(90px, 0.7fr));
    gap: 10px;
    align-items: center;
}
.ea-review-card .ea-detail-grid,
.ea-history-card .ea-detail-grid,
.ea-task-card .ea-detail-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}
.ea-timeline-page {
    position: relative;
    display: grid;
    gap: 12px;
}
.ea-timeline-card {
    border-left: 4px solid #2878ff;
}
.ea-stepper-line {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0;
    padding: 6px 0 4px;
}
.ea-stepper-step {
    position: relative;
    text-align: center;
    color: #66718f;
    font-size: 12px;
    font-weight: 900;
}
.ea-stepper-step:not(:last-child)::after {
    content: "";
    position: absolute;
    top: 15px;
    left: calc(50% + 18px);
    width: calc(100% - 36px);
    height: 2px;
    background: #dbe7f6;
}
.ea-stepper-dot {
    position: relative;
    z-index: 1;
    width: 30px;
    height: 30px;
    margin: 0 auto 7px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: #dfeaff;
    color: #3467b3;
}
.ea-stepper-step.active .ea-stepper-dot {
    background: #0b75ff;
    color: #fff;
    box-shadow: 0 0 0 8px #e9f2ff;
}
.ea-system-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}
.ea-system-item {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
}
@media (max-width: 1180px) {
    .ea-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .ea-detail-grid,
    .ea-review-card .ea-detail-grid,
    .ea-history-card .ea-detail-grid,
    .ea-task-card .ea-detail-grid,
    .ea-ledger-row,
    .ea-system-grid { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
    .ea-summary-grid { grid-template-columns: 1fr; }
    .ea-stepper-line { grid-template-columns: 1fr; gap: 8px; }
    .ea-stepper-step:not(:last-child)::after { display: none; }
}
</style>
"""


def _dashboard_shell(page_data: EventConsoleData, *, search_query: str = "") -> str:
    """Return the dashboard HTML shell."""
    metric_cards = _dashboard_metric_cards(page_data)
    return "\n".join(
        [
            '<div class="ea-shell">',
            '<div class="ea-grid">',
            _hero_html(page_data),
            "".join(_metric_card_html(metric) for metric in metric_cards),
            _top_events_html(page_data),
            _asset_watch_html(page_data),
            _causal_chain_html(page_data),
            _ledger_html(page_data),
            _lifecycle_html(page_data),
            _review_html(page_data),
            _rule_update_html(page_data),
            _data_status_html(page_data),
            _scheduler_status_html(page_data),
            "</div>",
            "</div>",
        ]
    )


def _hero_html(page_data: EventConsoleData) -> str:
    preview = page_data.daily_briefing_preview or {}
    chip = _source_chip(preview)
    has_report = bool(preview.get("has_report"))
    date_text = _h(preview.get("date") or "待生成")
    event_count = len(_homepage_top_events(page_data))
    briefing_status = f"今日简报已生成 · {date_text}" if has_report else "暂无今日简报 · 待生成"
    impact_status = "已更新" if has_report else "等待简报"
    return f"""
<section class="ea-card ea-hero">
  <div>
    <h1>今日事件研究总览</h1>
    <p>从事件发现、因果分析到自动复盘，帮助你持续跟踪事件对市场的影响。</p>
    {_page_link("每日简报", "查看今日简报 →", "ea-primary-btn")}
    <div class="ea-briefing-card">
      {chip}
      <span class="ea-briefing-main">{_h(briefing_status)}</span>
      <span>重点事件：{event_count} 件 · 市场影响评估：{_h(impact_status)}</span>
    </div>
  </div>
  <div class="ea-hero-art" aria-hidden="true">
    <div class="ea-radar"></div>
    <div class="ea-arrow"></div>
    <div class="ea-magnifier"></div>
  </div>
</section>
"""


def _dashboard_metric_cards(page_data: EventConsoleData) -> list[dict[str, Any]]:
    dashboard = page_data.dashboard
    review_results = max(
        int(dashboard.latest_review_result_count or 0),
        int(page_data.review_summary.get("复盘结果数") or 0),
    )
    health = _system_health_parts(page_data)
    data_note = "来自本地 Demo" if page_data.source_kind == "demo" else "来自本地数据"
    return [
        {
            "title": "本地事件数",
            "value": len(page_data.lifecycle_events) + len(page_data.background_events),
            "unit": "件",
            "note": data_note,
            "delta_class": "neutral",
            "color": "#2878ff",
        },
        {
            "title": "高优先级事件",
            "value": dashboard.urgent_count + dashboard.high_count,
            "unit": "件",
            "note": "等待历史对比数据",
            "delta_class": "neutral",
            "color": "#8f42ff",
        },
        {
            "title": "复盘结果",
            "value": review_results,
            "unit": "条",
            "note": "来自 ReviewResult",
            "delta_class": "neutral",
            "color": "#11a99c",
        },
        {
            "title": "规则更新",
            "value": dashboard.latest_rule_update_count or len(page_data.rule_updates),
            "unit": "条",
            "note": "来自 RuleUpdate",
            "delta_class": "neutral",
            "color": "#ff7a1a",
        },
        {
            "title": "系统健康状态",
            "kind": "health",
            "main": health["main"],
            "badge": health["badge"],
            "note": health["note"],
            "delta_class": "neutral",
            "color": "#18b985",
        },
    ]


def _metric_card_html(metric: dict[str, Any]) -> str:
    title = _h(metric["title"])
    delta_class = _h(metric["delta_class"])
    note = _h(metric.get("note") or "等待历史对比数据")
    spark_color = _h(metric["color"])
    if metric.get("kind") == "health":
        main = _h(metric.get("main") or "--")
        badge = _h(metric.get("badge") or "待确认")
        return f"""
<section class="ea-card ea-metric">
  <div class="ea-metric-title">{title}</div>
  <div class="ea-health-main">{main}</div>
  <div class="ea-health-row-inline"><span class="ea-health-badge">{badge}</span></div>
  <div class="ea-delta"><span class="{delta_class}">{note}</span></div>
  <div class="ea-spark" style="--spark:{spark_color}"></div>
</section>
"""
    value = _h(metric["value"])
    unit = _h(metric.get("unit", ""))
    return f"""
<section class="ea-card ea-metric">
  <div class="ea-metric-title">{title}</div>
  <div class="ea-metric-number">{value}<span>{unit}</span></div>
  <div class="ea-delta"><span class="{delta_class}">{note}</span></div>
  <div class="ea-spark" style="--spark:{spark_color}"></div>
</section>
"""


def _top_events_html(page_data: EventConsoleData) -> str:
    events = _homepage_top_events(page_data)
    if not events:
        return f"""
<section class="ea-card ea-section ea-top-events">
  <div class="ea-section-title"><h2>重点事件 Top 3</h2>{_page_link("事件中心", "查看全部 ›")}</div>
  <div class="ea-empty">暂无重点事件，请先运行 demo 或新闻扫描。</div>
</section>
"""
    count = len(events)
    grid_class = f"cols-{min(max(count, 1), 3)}"
    cards = []
    for index, event in enumerate(events, start=1):
        confidence = _confidence_text(event.get("可信度") or event.get("优先分"))
        indicators = list(event.get("验证指标") or event.get("后续验证指标") or event.get("重要原因") or [])[:3]
        impacts = _event_impact_labels(event, page_data)[:3]
        rank_color = "#ff3434" if index == 1 else "#ff8a1a" if index == 2 else "#f5a400"
        title = _h(event.get("标题") or "等待新增事件")
        summary = _h(event.get("摘要") or "事件仍在等待更多事实验证。")
        priority = _h(event.get("优先级说明") or "观察中")
        event_level = _h(event.get("事件等级") or event.get("阶段说明") or "--")
        initial = _h(_event_initial(event.get("标题")))
        indicator_items = "".join(f"<li>{_h(item)}</li>" for item in indicators) or "<li>未记录</li>"
        impact_chips = "".join(f'<span class="ea-chip signal">{_h(item)}</span>' for item in impacts) or '<span class="ea-chip neutral">影响方向未记录</span>'
        source_chip = _source_chip(event)
        card_class = "ea-event-card wide" if count == 1 else "ea-event-card"
        cards.append(
            f"""
<article class="{card_class}">
  <div class="ea-rank" style="background:{rank_color}">{index}</div>
  <div class="ea-event-head">
    <div class="ea-thumb">{initial}</div>
    <div>
      <div class="ea-event-title">{title}</div>
      <div class="ea-event-meta">
        <span class="ea-chip neutral">等级 {event_level}</span>
        {source_chip}
      </div>
    </div>
    <div>
      <span class="ea-tag">{priority}</span>
      <div class="ea-confidence">{confidence}</div>
    </div>
  </div>
  <div class="ea-caption" style="margin-top:8px;">一句话结论：{summary}</div>
  <div class="ea-chip-row">{impact_chips}</div>
  <ul class="ea-mini-list">
    {indicator_items}
  </ul>
</article>
"""
        )
    return f"""
<section class="ea-card ea-section ea-top-events">
  <div class="ea-section-title"><h2>重点事件 Top 3</h2>{_page_link("事件中心", "查看全部 ›")}</div>
  <div class="ea-event-cards {grid_class}">{''.join(cards)}</div>
</section>
"""


def _asset_watch_html(page_data: EventConsoleData) -> str:
    rows = page_data.asset_signal_rows[:5]
    if not rows:
        body = '<tr><td colspan="4"><div class="ea-empty">暂无资产映射信号，等待 EventCard / Prediction Ledger 接入。</div></td></tr>'
    else:
        body = "".join(
            f"""
<tr>
  <td><span class="ea-asset-cell"><span class="ea-asset-icon">{_h(_event_initial(row.get("资产/板块")))}</span>{_h(row.get("资产/板块") or "--")}</span></td>
  <td>{_h(row.get("关联事件") or "--")}</td>
  <td><span class="ea-chip">{_h(row.get("影响方向") or "--")}</span></td>
  <td>{_source_chip(row)}</td>
</tr>
"""
            for row in rows
        )
    return f"""
<section class="ea-card ea-section ea-asset-watch">
  <div class="ea-section-title"><h2>事件相关资产观察：研究信号</h2>{_page_link("事件中心", "查看全部 ›")}</div>
  <table class="ea-table">
    <thead><tr><th>资产/板块</th><th>关联事件</th><th>影响方向</th><th>信号来源</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</section>
"""


def _causal_chain_html(page_data: EventConsoleData) -> str:
    chain = page_data.causal_chain_view or {}
    evidence = page_data.causal_evidence_summary or {}
    nodes = chain.get("nodes") or []
    labels = ["事件", "变量", "行业", "资产"]
    nodes_html = "".join(
        f"""
<div class="ea-node">
  <div class="ea-node-icon">{_h(labels[index] if index < len(labels) else node.get("icon") or "")}</div>
  <div class="ea-node-label">{_h(node.get("label") or "--")}</div>
</div>
"""
        for index, node in enumerate(nodes[:4])
    )
    if not nodes_html:
        nodes_html = '<div class="ea-empty">暂无因果链数据，等待 EventCard causal_chain_summary 或 Prediction Ledger 接入。</div>'
    return f"""
<section class="ea-card ea-section ea-causal">
  <div class="ea-section-title"><h2>因果链影响分析：事件如何传导到资产</h2>{_source_chip(chain)}</div>
  <div class="ea-chain">
    {nodes_html}
  </div>
  <div class="ea-caption" style="margin-top:12px;">关键传导路径：{_h(chain.get("caption") or "暂无")}</div>
  <div class="ea-chip-row">
    {_label_chip_html(f"证据项 {evidence.get('total', 0)}")}
    {_label_chip_html(f"source {evidence.get('source', 0)}", "neutral")}
    {_label_chip_html(f"assumption {evidence.get('assumption', 0)}", "neutral")}
    {_label_chip_html(f"missing {evidence.get('missing', 0)}", "neutral")}
  </div>
</section>
"""


def _ledger_html(page_data: EventConsoleData) -> str:
    rows = page_data.prediction_ledger_rows[:5]
    if not rows:
        return f"""
<section class="ea-card ea-section ea-ledger">
  <div class="ea-section-title"><h2>预测账本：系统已记录的市场判断 <span class="ea-subtitle">Prediction Ledger</span></h2>{_page_link("预测账本", "查看全部 ›")}</div>
  <div class="ea-empty">暂无预测记录，请先运行事件分析流程。</div>
</section>
"""
    body = []
    for row in rows[:5]:
        direction = row.get("方向") or "未记录"
        color = "#ff3048" if str(direction).casefold() == "up" else "#00a989" if str(direction).casefold() == "down" else "#53668e"
        body.append(
            f"""
<tr>
  <td>{_h(row.get("事件") or "--")}</td>
  <td>{_h(row.get("资产") or "--")}</td>
  <td style="color:{color};font-weight:900;">{_h(direction)}</td>
  <td>{_h(row.get("时间窗口") or "--")}</td>
  <td>{_confidence_bar(row.get("因果置信度"))}</td>
  <td>{_confidence_bar(row.get("反伪相关后置信度"))}</td>
  <td><span class="ea-pill">{_h(row.get("状态") or "未记录")}</span></td>
</tr>
"""
        )
    return f"""
<section class="ea-card ea-section ea-ledger">
  <div class="ea-section-title"><h2>预测账本：系统已记录的市场判断 <span class="ea-subtitle">Prediction Ledger</span></h2>{_page_link("预测账本", "查看全部 ›")}</div>
  <table class="ea-table">
    <thead><tr><th>事件</th><th>影响资产</th><th>方向</th><th>时间窗口</th><th>因果置信度</th><th>反伪相关后置信度</th><th>复盘状态</th></tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table>
</section>
"""


def _lifecycle_html(page_data: EventConsoleData) -> str:
    summary = page_data.lifecycle_summary or {}
    counts = [(stage.get("label"), stage.get("count")) for stage in summary.get("stages", [])]
    if not counts:
        return """
<section class="ea-card ea-section ea-lifecycle">
  <div class="ea-section-title"><h2>事件生命周期追踪</h2><span class="ea-source-chip placeholder">待接入</span></div>
  <div class="ea-empty">暂无生命周期记录。</div>
</section>
"""
    stages = "".join(
        f"""
<div class="ea-stage {'active' if label in {'跟踪中', '已发现'} and count != '--' else ''}">
  <div class="ea-stage-dot">{index}</div>
  <div>{_h(label)}</div>
  <strong>{_h(count)}</strong>
</div>
"""
        for index, (label, count) in enumerate(counts, start=1)
    )
    current_events = summary.get("current_events") or []
    current_text = "；".join(
        f"{event.get('标题')}（{event.get('阶段说明') or event.get('阶段') or '--'}）"
        for event in current_events[:2]
        if event.get("标题")
    ) or "暂无重点事件"
    return f"""
<section class="ea-card ea-section ea-lifecycle">
  <div class="ea-section-title"><h2>事件生命周期追踪</h2>{_source_chip(summary)}</div>
  <div class="ea-timeline">{stages}</div>
  <div class="ea-caption" style="margin-top:12px;">当前重点事件：{_h(current_text)}</div>
</section>
"""


def _review_html(page_data: EventConsoleData) -> str:
    reviews = page_data.review_results[:4]
    if not reviews:
        return f"""
<section class="ea-card ea-section ea-review">
  <div class="ea-section-title"><h2>最近自动复盘结果</h2>{_page_link("自动复盘", "查看全部 ›")}</div>
  <div class="ea-empty">暂无自动复盘结果，请运行 auto_review_runner。</div>
</section>
"""
    body = []
    for review in reviews:
        validity = review.get("因果有效性") or "unknown"
        status = review.get("因果解释") or ("方向正确" if validity == "valid" else "因果待校正" if validity == "invalid" else "观察中")
        color = "#20ba84" if validity == "valid" else "#ff7a1a" if validity == "invalid" else "#6d7ca1"
        body.append(
            f"""
<tr>
  <td>{_h(review.get("资产") or "--")}</td>
  <td>{_h(review.get("窗口") or "--")}</td>
  <td>{_h(review.get("方向结果") or "方向待观察")}</td>
  <td>{_h(review.get("超额收益") or "--")}</td>
  <td><span class="ea-pill" style="background:{color}22;color:{color};">{_h(status)}</span></td>
</tr>
"""
        )
    return f"""
<section class="ea-card ea-section ea-review">
  <div class="ea-section-title"><h2>最近自动复盘结果</h2>{_page_link("自动复盘", "查看全部 ›")}</div>
  <table class="ea-table">
    <thead><tr><th>事件/资产</th><th>验证区间</th><th>方向判断</th><th>T+ 表现</th><th>综合结论</th></tr></thead>
    <tbody>{''.join(body)}</tbody>
  </table>
</section>
"""


def _rule_update_html(page_data: EventConsoleData) -> str:
    updates = page_data.rule_updates[:4]
    if not updates:
        return f"""
<section class="ea-card ea-section ea-rule">
  <div class="ea-section-title"><h2>规则更新动态</h2>{_page_link("规则更新", "查看全部规则更新 ›")}</div>
  <div class="ea-empty">暂无规则更新，等待复盘后生成。</div>
</section>
"""
    rows = []
    for update in updates:
        created_at = _h(str(update.get("创建时间", "--"))[:16])
        text = _h(update.get("RuleID") or update.get("标题") or "规则更新")
        action = _h(update.get("动作说明") or format_rule_update_action(update.get("动作")))
        weight = _h(update.get("权重变化") or "--")
        rows.append(
            f"""
<div class="ea-rule-row">
  <span class="ea-time-small">{created_at}</span>
  <span>{text}<br><span class="ea-caption">{action} · 影响预测数量：{_h(update.get("次数") or "--")}</span></span>
  <strong>{weight}</strong>
</div>
"""
        )
    return f"""
<section class="ea-card ea-section ea-rule">
  <div class="ea-section-title"><h2>规则更新动态</h2>{_page_link("规则更新", "查看全部规则更新 ›")}</div>
  <div class="ea-rule-list">{''.join(rows)}</div>
</section>
"""


def _data_status_html(page_data: EventConsoleData) -> str:
    status = page_data.data_status or {}
    report_count = status.get("reports_count", 0)
    ledger_label = "已连接" if status.get("ledger_exists") else "未发现"
    scheduler_label = "有运行记录" if page_data.scheduler_runs else "未运行"
    source_label = status.get("configured_sources") or "数据源：Demo + 本地缓存"
    return f"""
<section class="ea-card ea-section ea-status">
  <div class="ea-section-title"><h2>数据状态</h2></div>
  <div class="ea-status-grid">
    <div class="ea-status-item"><span>已配置新闻源</span><span class="ea-status-number" style="font-size:14px;">{_h(source_label)}</span></div>
    <div class="ea-status-item"><span>本地报告</span><span class="ea-status-number">{_h(report_count)}</span></div>
    <div class="ea-status-item"><span>Ledger</span><span class="ea-ok">{_h(ledger_label)}</span></div>
  </div>
  <div class="ea-caption" style="margin-top:12px;">调度记录：{_h(scheduler_label)}；{_source_chip(status)}</div>
</section>
"""


def _scheduler_status_html(page_data: EventConsoleData) -> str:
    rows = "".join(_scheduler_status_row(row) for row in page_data.scheduler_status_rows)
    note = '<div class="ea-empty" style="margin-bottom:8px;">暂无调度运行记录。</div>' if not page_data.scheduler_runs else ""
    if not rows:
        rows = '<div class="ea-empty">暂无调度运行记录。</div>'
    return f"""
<section class="ea-card ea-section ea-scheduler">
  <div class="ea-section-title"><h2>调度状态</h2>{_page_link("调度器状态", "查看调度日志 ›")}</div>
  {note}
  <div class="ea-health-list">{rows}</div>
</section>
"""


def _filter_page_data(page_data: EventConsoleData, query: str) -> EventConsoleData:
    needle = query.casefold().strip()
    if not needle:
        return page_data

    def keep(row: dict[str, Any]) -> bool:
        return needle in str(row).casefold()

    dashboard = page_data.dashboard.model_copy(
        update={
            "top_events": [row for row in page_data.dashboard.top_events if keep(row)],
            "recent_reviews": [row for row in page_data.dashboard.recent_reviews if keep(row)],
            "recent_rule_updates": [row for row in page_data.dashboard.recent_rule_updates if keep(row)],
        }
    )
    return page_data.model_copy(
        update={
            "dashboard": dashboard,
            "event_cards": [row for row in page_data.event_cards if keep(row)],
            "prediction_ledger_rows": [row for row in page_data.prediction_ledger_rows if keep(row)],
            "asset_signal_rows": [row for row in page_data.asset_signal_rows if keep(row)],
            "review_results": [row for row in page_data.review_results if keep(row)],
            "rule_updates": [row for row in page_data.rule_updates if keep(row)],
        }
    )


def _render_product_header(
    st: Any,
    title: str,
    subtitle: str,
    page_data: EventConsoleData,
    *,
    badges: list[str] | None = None,
) -> None:
    """Render the shared product page header."""
    badge_values = [value for value in (badges or []) if value]
    badge_values.append(page_data.source_label)
    badge_values.append(f"更新时间：{page_data.page_updated_at or '未记录'}")
    badges_html = "".join(_label_chip_html(value) for value in dict.fromkeys(badge_values))
    st.markdown(
        f"""
<div class="ea-page-shell">
  <section class="ea-page-header">
    <div class="ea-page-kicker">EventAlpha Research Console</div>
    <h1>{_h(title)}</h1>
    <p class="ea-page-subtitle">{_h(subtitle)}</p>
    <div class="ea-page-badges">{badges_html}</div>
  </section>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_summary_cards(st: Any, cards: list[tuple[Any, Any, Any]]) -> None:
    """Render compact summary cards."""
    html = ["<div class=\"ea-page-shell\"><div class=\"ea-summary-grid\">"]
    for title, value, note in cards:
        html.append(
            f"""
<section class="ea-summary-card">
  <div class="ea-summary-title">{_h(title)}</div>
  <div class="ea-summary-value">{_h(value if value not in {None, ''} else '--')}</div>
  <div class="ea-summary-note">{_h(note or '--')}</div>
</section>
"""
        )
    html.append("</div></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def _render_info_note(st: Any, title: str, text: str) -> None:
    st.markdown(
        f"""
<div class="ea-page-shell">
  <section class="ea-warning-card">
    <div class="ea-card-title">{_h(title)}</div>
    <div class="ea-caption" style="margin-top:6px;">{_h(text)}</div>
  </section>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_empty_state_html(st: Any, text: str) -> None:
    st.markdown(
        f'<div class="ea-page-shell"><div class="ea-empty">{_h(text)}</div></div>',
        unsafe_allow_html=True,
    )


def _render_risk_notice(st: Any) -> None:
    _render_info_note(st, "风险提示", RISK_DISCLAIMER)


def _evidence_rows_for_event(page_data: EventConsoleData, event_row: dict[str, Any]) -> list[dict[str, Any]]:
    event_id = str(event_row.get("事件ID") or "")
    title = str(event_row.get("标题") or "")
    rows = []
    for row in page_data.causal_evidence_rows:
        if event_id and row.get("事件ID") == event_id:
            rows.append(row)
        elif title and row.get("事件") == title:
            rows.append(row)
    return [
        {
            "步骤": row.get("step"),
            "证据类型": row.get("evidence_type"),
            "证据说明": row.get("evidence_text"),
            "来源": row.get("source") or "--",
            "置信度调整": row.get("confidence_adjustment"),
            "需要验证": "是" if row.get("verification_needed") else "否",
            "验证指标": row.get("verification_indicator") or "--",
        }
        for row in rows
    ]


def _source_label(row_or_data: Any) -> str:
    """Return a compact source label from any UI row/dict."""
    if isinstance(row_or_data, dict):
        return str(row_or_data.get("source_label") or row_or_data.get("来源标签") or "本地数据")
    return str(getattr(row_or_data, "source_label", "") or "本地数据")


def _options_from_rows(rows: list[dict[str, Any]], key: str) -> list[str]:
    values = sorted(
        {
            str(row.get(key)).strip()
            for row in rows
            if str(row.get(key) or "").strip() not in {"", "None", "暂无", "未记录", "--"}
        }
    )
    return ["全部", *values]


def _filter_exact(rows: list[dict[str, Any]], key: str, selected: str) -> list[dict[str, Any]]:
    if selected == "全部":
        return rows
    return [row for row in rows if str(row.get(key) or "") == selected]


def _latest_from_rows(rows: list[dict[str, Any]], key: str) -> str:
    values = sorted((str(row.get(key) or "") for row in rows if row.get(key)), reverse=True)
    return values[0] if values else "--"


def _briefing_sections_html(markdown: str) -> str:
    """Render Markdown briefing as simple product cards without inventing content."""
    sections = _markdown_sections(markdown)
    if not sections:
        return '<div class="ea-page-shell"><div class="ea-empty">暂无今日简报，请运行 daily_briefing job 或 run_full_demo。</div></div>'
    cards = []
    for title, lines in sections[:8]:
        is_warning = any(token in title for token in ("风险", "免责声明", "提示"))
        card_class = "ea-warning-card" if is_warning else "ea-briefing-section"
        cards.append(
            f"""
<section class="{card_class}">
  <h3>{_h(title)}</h3>
  {_markdown_lines_html(lines)}
</section>
"""
        )
    return f'<div class="ea-page-shell"><div class="ea-page-stack">{"".join(cards)}</div></div>'


def _markdown_sections(markdown: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = "简报摘要"
    current_lines: list[str] = []
    for raw_line in str(markdown or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if current_lines:
                sections.append((current_title, current_lines))
                current_lines = []
            current_title = line.lstrip("#").strip() or "简报摘要"
            continue
        current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))
    return sections


def _markdown_lines_html(lines: list[str]) -> str:
    items: list[str] = []
    paragraphs: list[str] = []
    for line in lines[:14]:
        stripped = line.lstrip("-*0123456789. ").strip()
        if not stripped:
            continue
        if line.startswith(("-", "*")) or line[:2].replace(".", "").isdigit():
            items.append(f"<li>{_h(stripped)}</li>")
        else:
            paragraphs.append(f'<p class="ea-caption">{_h(stripped)}</p>')
    ul = f"<ul>{''.join(items)}</ul>" if items else ""
    return "".join(paragraphs) + ul


def _event_cards_html(rows: list[dict[str, Any]], page_data: EventConsoleData) -> str:
    lifecycle_by_title = {
        str(row.get("标题")): row
        for row in page_data.lifecycle_events + page_data.background_events
        if row.get("标题")
    }
    cards = []
    for row in rows:
        lifecycle = lifecycle_by_title.get(str(row.get("标题"))) or {}
        assets = _chip_list(row.get("可能影响资产"), empty="影响资产未记录", limit=5)
        risks = _chip_list(row.get("风险因素"), empty="风险因素未记录", limit=3, kind="neutral")
        indicators = _chip_list(row.get("后续验证指标"), empty="验证指标未记录", limit=3, kind="signal")
        cards.append(
            f"""
<article class="ea-product-card">
  <div class="ea-card-title-row">
    <div>
      <div class="ea-card-title">{_h(row.get("标题") or "--")}</div>
      <div class="ea-chip-row">
        {_label_chip_html(f"等级 {row.get('事件等级') or '--'}")}
        {_label_chip_html(lifecycle.get("阶段说明") or lifecycle.get("阶段") or "生命周期未记录", "neutral")}
        {_source_chip(row)}
      </div>
    </div>
    <div class="ea-confidence">{_confidence_text(row.get("可信度"))}</div>
  </div>
  <div class="ea-caption">一句话结论：{_h(row.get("一句话摘要") or "--")}</div>
  <div class="ea-detail-grid" style="margin-top:12px;">
    <div class="ea-detail-item"><div class="ea-detail-label">可能影响资产</div><div class="ea-chip-row">{assets}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">风险因素</div><div class="ea-chip-row">{risks}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">后续验证指标</div><div class="ea-chip-row">{indicators}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">历史验证</div><div class="ea-detail-value">{_h(row.get("历史验证") or "--")}</div></div>
  </div>
</article>
"""
        )
    return f'<div class="ea-page-shell"><div class="ea-card-list">{"".join(cards)}</div></div>'


def _ledger_page_html(rows: list[dict[str, Any]]) -> str:
    cards = []
    for row in rows:
        cards.append(
            f"""
<article class="ea-product-card ea-ledger-row">
  <div>
    <div class="ea-card-title">{_h(_short_id(row.get("PredictionID")))} · {_h(row.get("事件") or "--")}</div>
    <div class="ea-caption">{_h(row.get("发布时间") or "--")} · {_source_chip(row)}</div>
  </div>
  <div>{_direction_chip_html(row.get("方向"))}<div class="ea-caption" style="margin-top:6px;">{_h(row.get("资产") or "--")}</div></div>
  <div><div class="ea-detail-label">时间窗口</div><div class="ea-detail-value">{_h(row.get("时间窗口") or "--")}</div></div>
  <div><div class="ea-detail-label">因果置信度</div>{_confidence_bar(row.get("因果置信度"))}</div>
  <div><div class="ea-detail-label">反伪相关后</div>{_confidence_bar(row.get("反伪相关后置信度"))}</div>
  <div><div class="ea-detail-label">最终 / 状态</div>{_confidence_bar(row.get("最终置信度"))}<div class="ea-chip-row">{_status_chip_html(row.get("状态"))}</div></div>
</article>
"""
        )
    return f'<div class="ea-page-shell"><div class="ea-ledger-list">{"".join(cards)}</div></div>'


def _reviews_page_html(rows: list[dict[str, Any]]) -> str:
    cards = []
    for row in rows:
        cards.append(
            f"""
<article class="ea-product-card ea-review-card">
  <div class="ea-card-title-row">
    <div>
      <div class="ea-card-title">{_h(row.get("资产") or "--")} · {_h(row.get("窗口") or "--")}</div>
      <div class="ea-chip-row">{_review_result_chip(row)}{_source_chip(row)}</div>
    </div>
    <div>{_h(row.get("超额收益") or "--")}</div>
  </div>
  <div class="ea-detail-grid">
    <div class="ea-detail-item"><div class="ea-detail-label">方向判断</div><div class="ea-detail-value">{_h(row.get("方向结果") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">Benchmark</div><div class="ea-detail-value">{_h(row.get("基准收益") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">因果有效性</div><div class="ea-detail-value">{_h(row.get("因果解释") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">错误类型</div><div class="ea-detail-value">{_h(row.get("错误解释") or row.get("错误类型") or "--")}</div></div>
  </div>
  <div class="ea-caption" style="margin-top:10px;">复盘解释：{_h(row.get("复盘解释") or "--")}</div>
</article>
"""
        )
    return f'<div class="ea-page-shell"><div class="ea-review-list">{"".join(cards)}</div></div>'


def _rule_updates_page_html(rows: list[dict[str, Any]]) -> str:
    cards = []
    for row in rows:
        cards.append(
            f"""
<article class="ea-timeline-card">
  <div class="ea-card-title-row">
    <div>
      <div class="ea-card-title">{_h(row.get("RuleID") or "--")}</div>
      <div class="ea-caption">{_h(row.get("创建时间") or "--")} · {_source_chip(row)}</div>
    </div>
    {_status_chip_html(row.get("动作说明") or format_rule_update_action(row.get("动作")))}
  </div>
  <div class="ea-detail-grid">
    <div class="ea-detail-item"><div class="ea-detail-label">更新动作</div><div class="ea-detail-value">{_h(row.get("动作说明") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">权重变化</div><div class="ea-detail-value">{_h(row.get("权重变化") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">影响预测数量</div><div class="ea-detail-value">{_h(row.get("次数") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">调整原因</div><div class="ea-detail-value">{_h(row.get("理由") or "--")}</div></div>
  </div>
</article>
"""
        )
    return f'<div class="ea-page-shell"><div class="ea-timeline-page">{"".join(cards)}</div></div>'


def _rule_feedback_panel_html(page_data: EventConsoleData) -> str:
    summary = page_data.rule_feedback_summary or {}
    signals = summary.get("signals") or []
    rows = "".join(
        f"""
<div class="ea-system-item">
  <div>
    <div class="ea-card-title">{_h(signal.get("rule_key") or "--")}</div>
    <div class="ea-caption">{_h(signal.get("reason") or "--")}</div>
  </div>
  {_label_chip_html(f"{float(signal.get('adjustment') or 0):+.2f}")}
</div>
"""
        for signal in signals[:4]
    ) or '<div class="ea-empty">暂无复盘反馈信号，请运行 run_rule_feedback_report。</div>'
    return f"""
<div class="ea-page-shell">
  <section class="ea-wide-card">
    <div class="ea-card-title-row">
      <div>
        <div class="ea-card-title">复盘反馈信号</div>
        <div class="ea-caption">ReviewResult / RuleUpdate 可反向校准下一次推理；本轮只展示信号，不写回 ledger。</div>
      </div>
      {_source_chip(summary)}
    </div>
    <div class="ea-system-grid">{rows}</div>
  </section>
  <div style="height:12px;"></div>
</div>
"""


def _lifecycle_page_html(rows: list[dict[str, Any]]) -> str:
    cards = []
    for row in rows:
        stage = str(row.get("阶段") or "")
        cards.append(
            f"""
<article class="ea-product-card">
  <div class="ea-card-title-row">
    <div>
      <div class="ea-card-title">{_h(row.get("标题") or row.get("短标题") or "--")}</div>
      <div class="ea-chip-row">{_status_chip_html(row.get("阶段说明") or stage)}{_source_chip(row)}</div>
    </div>
    <div class="ea-confidence">{_confidence_text(row.get("优先分"))}</div>
  </div>
  {_lifecycle_stepper_html(stage)}
  <div class="ea-detail-grid" style="margin-top:12px;">
    <div class="ea-detail-item"><div class="ea-detail-label">可信度</div><div class="ea-detail-value">{_h(row.get("可信度说明") or row.get("可信度") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">source_count</div><div class="ea-detail-value">{_h(row.get("来源数") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">latest_update_time</div><div class="ea-detail-value">{_h(row.get("最近出现") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">重要 lifecycle event</div><div class="ea-detail-value">{_h(row.get("最新变化") or "--")}</div></div>
  </div>
  <div class="ea-caption" style="margin-top:10px;">{_h(row.get("摘要") or "--")}</div>
</article>
"""
        )
    return f'<div class="ea-page-shell"><div class="ea-card-list">{"".join(cards)}</div></div>'


def _scheduler_page_html(page_data: EventConsoleData) -> str:
    if not page_data.scheduler_runs:
        note = '<div class="ea-empty">暂无调度运行记录。</div>'
    else:
        note = ""
    cards = []
    for row in page_data.scheduler_status_rows:
        cards.append(
            f"""
<article class="ea-task-card">
  <div class="ea-card-title-row">
    <div>
      <div class="ea-card-title">{_h(row.get("任务") or row.get("job_type") or "--")}</div>
      <div class="ea-caption">{_h(row.get("job_type") or "--")} · {_source_chip(row)}</div>
    </div>
    {_status_chip_html(row.get("状态") or "未运行")}
  </div>
  <div class="ea-detail-grid">
    <div class="ea-detail-item"><div class="ea-detail-label">最近运行时间</div><div class="ea-detail-value">{_h(row.get("最近运行时间") or "未运行")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">最近结果</div><div class="ea-detail-value">{_h(row.get("最近结果") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">数据来源</div><div class="ea-detail-value">{_h(row.get("信号来源") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">错误摘要</div><div class="ea-detail-value">--</div></div>
  </div>
</article>
"""
        )
    return f'<div class="ea-page-shell"><div class="ea-task-list">{note}{"".join(cards)}</div></div>'


def _historical_cases_html(rows: list[dict[str, Any]]) -> str:
    cards = []
    for row in rows:
        cards.append(
            f"""
<article class="ea-product-card ea-history-card">
  <div class="ea-card-title-row">
    <div>
      <div class="ea-card-title">{_h(row.get("案例名称") or "--")}</div>
      <div class="ea-chip-row">
        {_label_chip_html(row.get("事件类型") or "--")}
        {_label_chip_html(row.get("事件日期") or "--", "neutral")}
        {_source_chip(row)}
      </div>
    </div>
    {_status_chip_html(row.get("因果有效性") or "unknown")}
  </div>
  <div class="ea-caption">摘要：{_h(row.get("摘要") or "--")}</div>
  <div class="ea-detail-grid" style="margin-top:12px;">
    <div class="ea-detail-item"><div class="ea-detail-label">affected_assets</div><div class="ea-chip-row">{_chip_list(row.get("影响资产"), empty="未记录")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">historical outcome</div><div class="ea-detail-value">{_h(row.get("市场反应") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">causal assessment</div><div class="ea-detail-value">{_h(row.get("预期方向") or "--")} / {_h(row.get("实际方向") or "--")}</div></div>
    <div class="ea-detail-item"><div class="ea-detail-label">reliability</div><div class="ea-detail-value">{_h(row.get("结果质量") or "--")}</div></div>
  </div>
  <div class="ea-chip-row" style="margin-top:10px;">{_chip_list(row.get("标签"), empty="标签未记录", kind="neutral")}</div>
</article>
"""
        )
    return f'<div class="ea-page-shell"><div class="ea-history-list">{"".join(cards)}</div></div>'


def _system_status_html(page_data: EventConsoleData) -> str:
    status = page_data.data_status or {}
    items = [
        ("数据源", status.get("configured_sources") or "Demo / 本地缓存", "已配置新闻源，不代表实时行情"),
        ("Reports", f"{status.get('reports_count', 0)} 个", status.get("latest_report_path") or "暂无报告"),
        ("Ledger", "已连接" if status.get("ledger_exists") else "未发现", "SQLite 只读检查"),
        ("Lifecycle Store", "已连接" if status.get("lifecycle_store_exists") else "未发现", "event_lifecycle_store.json"),
        ("Scheduler State", "已连接" if status.get("scheduler_state_exists") else "未发现", "scheduler_state.json"),
        ("Scheduler Runs", "已连接" if status.get("scheduler_runs_exists") else "未发现", "scheduler_runs.jsonl"),
        ("Historical Cases", "已连接" if status.get("historical_cases_exists") else "未发现", status.get("historical_cases_path") or "暂无"),
        ("当前模式", "Demo" if page_data.source_kind == "demo" else "Normal", page_data.source_label),
    ]
    cards = []
    for title, value, note in items:
        chip_kind = "neutral" if value in {"未发现", "暂无"} else "signal"
        cards.append(
            f"""
<div class="ea-system-item">
  <div>
    <div class="ea-card-title">{_h(title)}</div>
    <div class="ea-caption" style="margin-top:4px;">{_h(note)}</div>
  </div>
  {_label_chip_html(value, chip_kind)}
</div>
"""
        )
    notes = "".join(f"<li>{_h(note)}</li>" for note in status.get("notes", []) or [])
    notes_html = f'<section class="ea-wide-card"><div class="ea-card-title">本地状态说明</div><ul>{notes}</ul></section>' if notes else ""
    capability_html = _capability_status_html(page_data)
    return f'<div class="ea-page-shell"><div class="ea-system-grid">{"".join(cards)}</div><div style="height:12px;"></div>{capability_html}<div style="height:12px;"></div>{notes_html}</div>'


def _capability_status_html(page_data: EventConsoleData) -> str:
    summaries = [
        page_data.source_coverage_summary,
        page_data.search_quality_summary,
        page_data.rule_feedback_summary,
        page_data.push_outbox_summary,
    ]
    rows = []
    for summary in summaries:
        title = summary.get("title") or "--"
        if title == "信息源覆盖状态":
            value = f"ok {summary.get('ok_count')} / placeholder {summary.get('placeholder_count')}"
        elif title == "搜索质量评估":
            value = f"raw {summary.get('raw_news_count')} / cluster {summary.get('cluster_count')}"
        elif title == "复盘反馈信号":
            value = f"signals {summary.get('signal_count')}"
        else:
            value = f"messages {summary.get('message_count')}"
        rows.append(
            f"""
<div class="ea-system-item">
  <div>
    <div class="ea-card-title">{_h(title)}</div>
    <div class="ea-caption">{_h(summary.get("path") or "暂无报告")}</div>
  </div>
  <div>{_label_chip_html(summary.get("status") or "暂无报告", "neutral")}<div class="ea-caption" style="margin-top:5px;text-align:right;">{_h(value)}</div></div>
</div>
"""
        )
    return f"""
<section class="ea-wide-card">
  <div class="ea-card-title-row">
    <div>
      <div class="ea-card-title">智能体能力进展</div>
      <div class="ea-caption">信息源覆盖、搜索质量、复盘反馈和推送 outbox 均来自本地报告；缺失时显示待生成。</div>
    </div>
  </div>
  <div class="ea-system-grid">{''.join(rows)}</div>
</section>
"""


def _label_chip_html(label: Any, kind: str = "signal") -> str:
    return f'<span class="ea-chip {kind}">{_h(label if label not in {None, ""} else "--")}</span>'


def _chip_list(values: Any, *, empty: str = "--", limit: int = 5, kind: str = "signal") -> str:
    items = [str(item).strip() for item in values or [] if str(item).strip()]
    if not items:
        return _label_chip_html(empty, "neutral")
    return "".join(_label_chip_html(item, kind) for item in items[:limit])


def _direction_chip_html(value: Any) -> str:
    text = str(value or "未记录")
    lowered = text.casefold()
    kind = "signal" if lowered in {"up", "long", "positive"} or "上" in text else "neutral"
    return _label_chip_html(text, kind)


def _status_chip_html(value: Any) -> str:
    text = str(value or "未记录")
    lowered = text.casefold()
    kind = "signal" if lowered in {"成功", "success", "valid", "方向正确", "正常", "active", "tracking"} else "neutral"
    if lowered in {"failed", "失败", "invalid", "因果需修正"}:
        kind = "neutral"
    return _label_chip_html(text, kind)


def _review_result_chip(row: dict[str, Any]) -> str:
    validity = str(row.get("因果有效性") or "unknown")
    if validity == "valid":
        return _status_chip_html("方向正确")
    if validity == "invalid":
        return _status_chip_html("因果需修正")
    return _status_chip_html("观察中")


def _lifecycle_stepper_html(stage: str) -> str:
    stages = [
        ("已发现", {"new", "developing", "confirmed", "analysis_only", "stale", "closed", "resolved"}),
        ("已验证", {"confirmed"}),
        ("已分析", {"analysis_only"}),
        ("已发布", {"published"}),
        ("跟踪中", {"developing", "new"}),
        ("已复盘", {"reviewed", "closed", "resolved", "stale"}),
    ]
    stage_text = str(stage or "").casefold()
    steps = []
    for index, (label, values) in enumerate(stages, start=1):
        active = " active" if stage_text in values else ""
        steps.append(
            f'<div class="ea-stepper-step{active}"><div class="ea-stepper-dot">{index}</div><div>{_h(label)}</div></div>'
        )
    return f'<div class="ea-stepper-line">{"".join(steps)}</div>'


def _short_id(value: Any) -> str:
    text = str(value or "--")
    return text if len(text) <= 14 else f"{text[:6]}…{text[-4:]}"


def _source_chip(row: dict[str, Any] | None) -> str:
    row = row or {}
    kind = str(row.get("source_kind") or "placeholder")
    label = str(row.get("source_label") or row.get("来源标签") or ("待接入" if kind == "placeholder" else "本地数据"))
    css_kind = kind if kind in {"demo", "placeholder"} else "real"
    return f'<span class="ea-source-chip {css_kind}">{_h(label)}</span>'


def _page_link(page: str, label: str, css_class: str = "ea-section-link") -> str:
    """Return an in-app link handled by app_streamlit._sync_query_page."""
    return f'<a class="{_h(css_class)}" href="?page={quote(page, safe="")}" target="_self">{_h(label)}</a>'


def _homepage_top_events(page_data: EventConsoleData) -> list[dict[str, Any]]:
    """Return homepage events without padding or fake placeholders."""
    events = [dict(row) for row in page_data.dashboard.top_events[:3]]
    if events:
        return events
    return [
        {
            "标题": row.get("标题"),
            "摘要": row.get("一句话摘要"),
            "优先级说明": row.get("事件等级"),
            "事件等级": row.get("事件等级"),
            "可信度": row.get("可信度"),
            "可信度说明": "事件卡片",
            "验证指标": row.get("后续验证指标", []),
            "可能影响资产": row.get("可能影响资产", []),
            "source_kind": row.get("source_kind"),
            "source_label": row.get("source_label"),
        }
        for row in page_data.event_cards[:3]
    ]


def _event_impact_labels(event: dict[str, Any], page_data: EventConsoleData) -> list[str]:
    """Collect impact labels already present in EventCard/Ledger-derived data."""
    title = str(event.get("标题") or "").strip()
    labels: list[str] = []
    for item in event.get("可能影响资产") or []:
        text = str(item or "").strip()
        if text and text not in labels:
            labels.append(text)
    for row in page_data.asset_signal_rows:
        related_event = str(row.get("关联事件") or "")
        if title and title not in related_event and related_event not in title:
            continue
        asset = str(row.get("资产/板块") or "").strip()
        direction = str(row.get("影响方向") or "").strip()
        text = " / ".join(part for part in [asset, direction] if part)
        if text and text not in labels:
            labels.append(text)
    return labels


def _confidence_text(value: Any) -> str:
    if value in {None, "", "未记录", "暂无"}:
        return "--"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if 0 <= number <= 1:
        return f"{number * 100:.0f}%"
    return f"{number:.0f}"


def _confidence_bar(value: Any) -> str:
    if value in {None, "", "未记录", "暂无"}:
        return "--"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _h(value)
    pct = number * 100 if 0 <= number <= 1 else number
    pct = max(0, min(pct, 100))
    return f'{number:.2f}<div class="ea-progress"><span style="width:{pct:.0f}%"></span></div>'


def _system_health_label(page_data: EventConsoleData) -> tuple[str, str]:
    if page_data.source_kind == "demo":
        return "本地 Demo", "正常；部分数据源未接入"
    if not page_data.scheduler_runs:
        return "未启动长期服务", "调度记录：未运行"
    if page_data.scheduler_status_counts.get("failed", 0):
        return "存在失败记录", "请查看调度日志"
    if page_data.scheduler_status_counts.get("success", 0):
        return "调度记录正常", "最近一次生成"
    return "本地只读", "部分数据源未接入"


def _system_health_parts(page_data: EventConsoleData) -> dict[str, str]:
    """Split health text so the KPI card does not render a long fake status."""
    if page_data.source_kind == "demo":
        return {"main": "本地 Demo", "badge": "正常", "note": "部分数据源未接入"}
    if not page_data.scheduler_runs:
        return {"main": "未启动服务", "badge": "未运行", "note": "调度记录：未运行"}
    if page_data.scheduler_status_counts.get("failed", 0):
        return {"main": "调度异常", "badge": "需检查", "note": "请查看调度日志"}
    if page_data.scheduler_status_counts.get("success", 0):
        return {"main": "本地调度", "badge": "正常", "note": "最近一次生成"}
    return {"main": "本地只读", "badge": "待确认", "note": "部分数据源未接入"}


def _scheduler_status_row(row: dict[str, Any]) -> str:
    status = str(row.get("状态") or "未运行")
    css_class = "ea-ok" if status in {"成功", "演练", "等待中"} else ""
    return (
        '<div class="ea-health-row">'
        f'<span>{_h(row.get("任务") or row.get("job_type") or "--")}<br>'
        f'<span class="ea-caption">{_h(row.get("最近运行时间") or "未运行")} · {_h(row.get("信号来源") or "--")}</span></span>'
        f'<span class="{css_class}">{_h(status)}</span>'
        "</div>"
    )


def _first_event_title(page_data: EventConsoleData) -> str:
    if page_data.dashboard.top_events:
        return str(page_data.dashboard.top_events[0].get("标题") or "暂无重点事件")
    if page_data.event_cards:
        return str(page_data.event_cards[0].get("标题") or "暂无重点事件")
    return "暂无重点事件"


def _event_initial(title: Any) -> str:
    text = str(title or "EA").strip()
    if "AI" in text.upper():
        return "AI"
    return text[:1] or "E"


def _h(value: Any) -> str:
    return escape(str(value if value is not None else ""))


def _render_lifecycle_cards(st: Any, rows: list[dict[str, Any]], empty_text: str) -> None:
    if not rows:
        st.info(empty_text)
        return
    table_rows = [
        {
            "标题": row["短标题"],
            "阶段": row["阶段说明"],
            "来源数": row["来源数"],
            "可信度": row["可信度说明"],
            "最近出现": row["最近出现"],
            "最新变化": row["最新变化"],
        }
        for row in rows
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
    for row in rows[:10]:
        with st.expander(row["标题"]):
            st.write(row["摘要"])
            st.write(f"来源：{row['来源']}")
            st.write(f"优先级：{row['优先级说明']}；优先分：{row['优先分']}")
            for reason in row.get("重要原因", [])[:3]:
                st.write(f"- {reason}")


def _render_table_or_empty(st: Any, rows: list[dict[str, Any]], empty_text: str) -> None:
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(empty_text)


def _render_key_value_table(st: Any, values: dict[str, int]) -> None:
    rows = [{"类型": key, "数量": value} for key, value in values.items()]
    _render_table_or_empty(st, rows, "暂无数据。")
