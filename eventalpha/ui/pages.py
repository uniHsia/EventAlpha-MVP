"""Streamlit page renderers for the read-only event console."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from eventalpha.briefing import DailyBriefingBuilder, MarkdownBriefingRenderer
from eventalpha.schemas.base import RISK_DISCLAIMER

from .components import EventConsoleData
from .formatters import (
    format_return_pct,
    format_rule_update_action,
)


def render_dashboard(st: Any, page_data: EventConsoleData) -> None:
    """Render the teacher-friendly dashboard page."""
    st.title("EventAlpha 热点事件驱动投资研究 Agent 控制台")
    st.caption("本地只读演示 · 事件发现 / 因果分析 / 历史验证 / 自动复盘")
    st.info("本页面展示本地数据闭环：从事件进入生命周期跟踪，到生成事件卡片，再到自动复盘和规则更新。")

    metric_cards = page_data.dashboard.metric_cards
    for start in range(0, len(metric_cards), 4):
        cols = st.columns(min(4, len(metric_cards) - start))
        for col, metric in zip(cols, metric_cards[start : start + 4]):
            col.metric(metric.label, metric.value)
            col.caption(metric.help_text)

    if page_data.dashboard.friendly_warnings:
        st.info("\n".join(page_data.dashboard.friendly_warnings))
        with st.expander("展开查看原始 warning"):
            st.write(page_data.dashboard.raw_warnings)

    st.subheader("今日重点事件 Top 3")
    if page_data.dashboard.top_events:
        for item in page_data.dashboard.top_events:
            with st.container(border=True):
                st.markdown(f"**{item['标题']}**")
                st.caption(
                    f"{item['优先级说明']} · {item['阶段说明']} · 来源：{item['来源']} · 可信度：{item['可信度说明']}"
                )
                st.write(item["摘要"])
                st.write(f"为什么重要：{item.get('为什么重要', '事件仍在发展，值得继续观察。')}")
                for indicator in item.get("验证指标", [])[:2]:
                    st.write(f"验证指标：{indicator}")
    else:
        st.info("暂无重点事件。")

    st.subheader("最近自动复盘结果")
    st.caption("当前为 mock/demo 复盘数据，仅用于演示闭环。")
    if page_data.dashboard.recent_reviews:
        for review in page_data.dashboard.recent_reviews:
            with st.container(border=True):
                st.markdown(f"**{review['资产']} / {review['窗口']}**")
                st.write(review["复盘解释"])
                st.caption(
                    f"{review['方向结果']} · {review['因果解释']} · 超额收益：{review['超额收益']} · {review['错误解释']}"
                )
    else:
        st.info("暂无自动复盘结果。")

    st.subheader("最近规则更新")
    if page_data.dashboard.recent_rule_updates:
        for update in page_data.dashboard.recent_rule_updates:
            with st.container(border=True):
                st.markdown(f"**{update['标题']}**")
                st.write(update["中文解释"])
                st.caption(f"{update['动作说明']} · {update['权重变化']} · 最近时间：{update['创建时间']}")
    else:
        st.info("暂无规则更新。")

    st.subheader("系统状态说明")
    for note in page_data.dashboard.system_status_notes:
        st.write(f"- {note}")
    st.markdown(f"> {page_data.dashboard.risk_disclaimer}")


def render_daily_briefing(
    st: Any,
    page_data: EventConsoleData,
    *,
    collected_data: Any,
    selected_date: date,
) -> None:
    """Render the daily briefing page."""
    st.title("每日事件研究简报")
    st.caption("该页面展示由本地事件、复盘和调度日志生成的 Markdown 简报。")
    if page_data.scheduler_warnings:
        with st.expander("数据源提示 / Warnings"):
            st.write(page_data.scheduler_warnings)

    if st.button("刷新 preview"):
        st.rerun()

    markdown = page_data.daily_briefing_markdown
    json_payload = page_data.daily_briefing_json
    if not markdown:
        briefing = DailyBriefingBuilder().build(collected_data)
        markdown = MarkdownBriefingRenderer().render(briefing)
        json_payload = briefing.model_dump(mode="json")
        st.info(f"{selected_date.isoformat()} 没有本地 report，以下为只读 preview，不会落盘。")

    cols = st.columns(2)
    cols[0].download_button(
        "下载 Markdown",
        data=markdown,
        file_name=f"daily_briefing_{selected_date:%Y%m%d}.md",
        mime="text/markdown",
    )
    cols[1].download_button(
        "下载 JSON",
        data=json.dumps(json_payload, ensure_ascii=False, indent=2),
        file_name=f"daily_briefing_{selected_date:%Y%m%d}.json",
        mime="application/json",
    )
    st.markdown(markdown)


def render_event_cards(st: Any, page_data: EventConsoleData) -> None:
    """Render EventCard rows as cards first and table second."""
    st.title("事件卡片")
    st.caption("事件卡片汇总一条事件的影响链、风险因素和后续验证指标。")
    cols = st.columns([1, 2])
    level = cols[0].selectbox("事件等级", ["全部", "A", "B", "C"], index=0)
    query = cols[1].text_input("文本搜索", "")
    rows = page_data.event_cards
    if level != "全部":
        rows = [row for row in rows if row.get("事件等级") == level]
    if query:
        needle = query.casefold()
        rows = [row for row in rows if needle in str(row).casefold()]

    st.metric("事件卡片数", len(rows))
    st.caption(f"重复折叠数：{page_data.event_card_duplicate_total}。重复折叠表示相似事件卡片只展示最新一条。")

    if not rows:
        st.info("暂无 EventCard。")
    for row in rows[:10]:
        with st.expander(f"{row['事件等级']} · {row['标题']}", expanded=True):
            st.write(row["一句话摘要"])
            if row["可能影响资产"]:
                st.write("可能影响资产：")
                for item in row["可能影响资产"][:5]:
                    st.write(f"- {item}")
            st.write("风险因素：")
            for risk in row["风险因素"][:4] or ["暂无"]:
                st.write(f"- {risk}")
            st.write("后续验证指标：")
            for verification in row["后续验证指标"][:4] or ["暂无"]:
                st.write(f"- {verification}")
            st.caption(row["重复说明"])
            if row["历史验证"] != "暂无":
                st.info(row["历史验证"])

    with st.expander("原始表格"):
        _render_table_or_empty(st, rows, "暂无 EventCard。")


def render_lifecycle(st: Any, page_data: EventConsoleData) -> None:
    """Render lifecycle events."""
    st.title("事件生命周期追踪")
    st.caption("developing 表示系统仍在跟踪；analysis_only 表示背景分析或评论类内容。")
    stage = st.selectbox("阶段过滤", ["全部", "developing", "analysis_only", "stale", "closed", "new", "confirmed"], index=0)
    foreground = page_data.lifecycle_events
    background = page_data.background_events
    rows = foreground + background
    if stage != "全部":
        rows = [row for row in rows if row.get("阶段") == stage]

    active_rows = [row for row in rows if not row.get("背景分析")]
    background_rows = [row for row in rows if row.get("背景分析")]
    st.subheader("重点 / 活跃事件")
    _render_lifecycle_cards(st, active_rows, "暂无重点 lifecycle 事件。")

    with st.expander("背景观察 / analysis-only"):
        _render_lifecycle_cards(st, background_rows, "暂无背景观察事件。")


def render_reviews(st: Any, page_data: EventConsoleData) -> None:
    """Render review results."""
    st.title("自动复盘结果")
    st.caption("当前为 mock/demo 复盘数据，仅用于演示闭环。")
    summary = page_data.review_summary
    cols = st.columns(4)
    cols[0].metric("复盘结果数", summary.get("复盘结果数", 0))
    cols[1].metric("因果链支持", summary.get("valid", 0))
    cols[2].metric("未验证", summary.get("invalid", 0))
    cols[3].metric("观察/未知", summary.get("unknown", 0))
    st.caption(f"平均超额收益：{format_return_pct(summary.get('平均超额收益'), signed=True)}")

    validity = st.selectbox("因果有效性过滤", ["全部", "valid", "invalid", "unknown"], index=0)
    rows = page_data.review_results
    if validity != "全部":
        rows = [row for row in rows if row.get("因果有效性") == validity]
    if not rows:
        st.info("暂无 ReviewResult。")
    for row in rows[:10]:
        with st.container(border=True):
            st.markdown(f"**{row['资产']} / {row['窗口']}**")
            st.write(row["复盘解释"])
            st.caption(f"{row['方向结果']} · {row['因果解释']} · {row['错误解释']}")
    with st.expander("原始表格"):
        _render_table_or_empty(st, rows, "暂无 ReviewResult。")


def render_rule_updates(st: Any, page_data: EventConsoleData) -> None:
    """Render aggregated rule updates."""
    st.title("规则更新")
    st.caption("规则更新来自复盘结果，用于强化或削弱事件到资产映射规则；当前 demo/mock 数据不代表真实市场结论。")
    action = st.selectbox("动作过滤", ["全部", "strengthen", "weaken", "slightly_strengthen", "unchanged"], index=0)
    rows = page_data.rule_updates
    if action != "全部":
        rows = [row for row in rows if row.get("动作") == action]
    if not rows:
        st.info("暂无 RuleUpdate。")
    for row in rows:
        with st.expander(row["标题"], expanded=True):
            st.write(row["中文解释"])
            st.write(f"动作：{row['动作说明']}；次数：{row['次数']}；权重：{row['权重变化']}")
            st.write(f"理由：{row['理由']}")
            st.caption(f"最近更新时间：{row['创建时间']}")
    with st.expander("聚合表格"):
        _render_table_or_empty(st, rows, "暂无 RuleUpdate。")


def render_scheduler_status(st: Any, page_data: EventConsoleData) -> None:
    """Render scheduler status in a presentation-friendly way."""
    st.title("调度器状态")
    status_counts = page_data.scheduler_status_counts
    cols = st.columns(4)
    cols[0].metric("成功运行", status_counts.get("success", 0))
    cols[1].metric("dry-run 次数", status_counts.get("dry_run", 0))
    cols[2].metric("最近自动复盘", page_data.dashboard.latest_auto_review_status)
    cols[3].metric("最近日报", page_data.scheduler_job_type_counts.get("daily_briefing", 0))

    if page_data.friendly_scheduler_warnings:
        st.info("\n".join(page_data.friendly_scheduler_warnings))
        with st.expander("展开查看详细 warning"):
            st.write(page_data.scheduler_warnings)

    st.subheader("运行状态统计")
    _render_key_value_table(st, page_data.scheduler_status_counts)
    st.subheader("最近任务类型")
    _render_key_value_table(st, page_data.scheduler_job_type_counts)

    with st.expander("Configured Jobs"):
        _render_table_or_empty(st, page_data.scheduler_jobs, "暂无 scheduler config。")
    with st.expander("Tracking Policies"):
        _render_table_or_empty(st, page_data.tracking_policies, "暂无 tracking policies。")
    with st.expander("Recent Runs"):
        _render_table_or_empty(st, page_data.scheduler_runs, "暂无 scheduler run log。")
    with st.expander("开发者调试信息"):
        st.json(page_data.raw_debug)


def render_footer(st: Any) -> None:
    """Render compliance footer."""
    st.divider()
    st.caption(RISK_DISCLAIMER)


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
