"""Streamlit page renderers for the read-only event console."""

from __future__ import annotations

from datetime import date
from typing import Any

from eventalpha.briefing import DailyBriefingBuilder, MarkdownBriefingRenderer
from eventalpha.schemas.base import RISK_DISCLAIMER

from .components import EventConsoleData


def render_dashboard(st: Any, page_data: EventConsoleData) -> None:
    """Render the dashboard page."""
    st.title("EventAlpha Event Console")
    st.caption("本地只读控制台 · demo/mock 数据需明确区分 · 不构成投资建议")
    summary = page_data.dashboard
    cols = st.columns(4)
    cols[0].metric("Urgent", summary.urgent_count)
    cols[1].metric("High", summary.high_count)
    cols[2].metric("Normal", summary.normal_count)
    cols[3].metric("Background", summary.background_count)
    cols = st.columns(3)
    cols[0].metric("Auto Review", summary.latest_auto_review_status)
    cols[1].metric("ReviewResults", summary.latest_review_result_count)
    cols[2].metric("RuleUpdates", summary.latest_rule_update_count)
    if summary.warnings:
        st.warning("\n".join(summary.warnings))
    for note in summary.notes[:5]:
        st.info(note)
    st.markdown(f"> {summary.risk_disclaimer}")


def render_daily_briefing(
    st: Any,
    page_data: EventConsoleData,
    *,
    collected_data: Any,
    selected_date: date,
) -> None:
    """Render the daily briefing page."""
    st.title("Daily Briefing")
    st.caption("优先展示本地报告文件；缺失时仅在内存中生成 preview，不落盘。")
    if st.button("刷新 preview"):
        st.rerun()
    markdown = page_data.daily_briefing_markdown
    if not markdown:
        briefing = DailyBriefingBuilder().build(collected_data)
        markdown = MarkdownBriefingRenderer().render(briefing)
        st.info(f"{selected_date.isoformat()} 没有本地 report，以下为只读 preview。")
    st.markdown(markdown)


def render_event_cards(st: Any, page_data: EventConsoleData) -> None:
    """Render EventCard rows."""
    st.title("Event Cards")
    level = st.selectbox("等级过滤", ["全部", "A", "B", "C"], index=0)
    query = st.text_input("文本搜索", "")
    rows = page_data.event_cards
    if level != "全部":
        rows = [row for row in rows if row.get("等级") == level]
    if query:
        needle = query.casefold()
        rows = [row for row in rows if needle in str(row).casefold()]
    _render_table_or_empty(st, rows, "暂无 EventCard。")
    for row in rows[:10]:
        with st.expander(str(row.get("标题"))):
            st.write(row.get("摘要"))
            st.write({"风险": row.get("风险"), "验证": row.get("验证"), "重复数": row.get("重复数")})
            if row.get("历史验证") != "暂无":
                st.write(row.get("历史验证"))


def render_lifecycle(st: Any, page_data: EventConsoleData) -> None:
    """Render lifecycle events."""
    st.title("Lifecycle")
    stage = st.selectbox("阶段过滤", ["全部", "developing", "analysis_only", "stale", "closed", "new", "confirmed"], index=0)
    foreground = page_data.lifecycle_events
    background = page_data.background_events
    rows = foreground + background
    if stage != "全部":
        rows = [row for row in rows if row.get("阶段") == stage]
    st.subheader("重点 / 活跃事件")
    _render_table_or_empty(st, [row for row in rows if not row.get("背景分析")], "暂无重点 lifecycle 事件。")
    st.subheader("背景观察 / analysis-only")
    _render_table_or_empty(st, [row for row in rows if row.get("背景分析")], "暂无背景观察事件。")


def render_reviews(st: Any, page_data: EventConsoleData) -> None:
    """Render review results."""
    st.title("Reviews")
    validity = st.selectbox("因果有效性过滤", ["全部", "valid", "invalid", "unknown"], index=0)
    rows = page_data.review_results
    if validity != "全部":
        rows = [row for row in rows if row.get("因果有效性") == validity]
    _render_table_or_empty(st, rows, "暂无 ReviewResult。")


def render_rule_updates(st: Any, page_data: EventConsoleData) -> None:
    """Render aggregated rule updates."""
    st.title("Rule Updates")
    action = st.selectbox("动作过滤", ["全部", "strengthen", "weaken", "slightly_strengthen", "unchanged"], index=0)
    rows = page_data.rule_updates
    if action != "全部":
        rows = [row for row in rows if row.get("动作") == action]
    _render_table_or_empty(st, rows, "暂无 RuleUpdate。")


def render_scheduler_status(st: Any, page_data: EventConsoleData) -> None:
    """Render scheduler status."""
    st.title("Scheduler Status")
    summary = page_data.dashboard
    cols = st.columns(4)
    cols[0].metric("Urgent", summary.urgent_count)
    cols[1].metric("High", summary.high_count)
    cols[2].metric("Normal", summary.normal_count)
    cols[3].metric("Background", summary.background_count)
    st.subheader("Run Status Counts")
    st.write(page_data.scheduler_status_counts or {})
    st.subheader("Recent Job Types")
    st.write(page_data.scheduler_job_type_counts or {})
    if page_data.scheduler_warnings:
        st.warning("\n".join(page_data.scheduler_warnings))
    st.subheader("Configured Jobs")
    _render_table_or_empty(st, page_data.scheduler_jobs, "暂无 scheduler config。")
    st.subheader("Recent Runs")
    _render_table_or_empty(st, page_data.scheduler_runs, "暂无 scheduler run log。")
    st.subheader("Tracking Policies")
    _render_table_or_empty(st, page_data.tracking_policies, "暂无 tracking policies。")


def render_footer(st: Any) -> None:
    """Render compliance footer."""
    st.divider()
    st.caption(RISK_DISCLAIMER)


def _render_table_or_empty(st: Any, rows: list[dict[str, Any]], empty_text: str) -> None:
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info(empty_text)
