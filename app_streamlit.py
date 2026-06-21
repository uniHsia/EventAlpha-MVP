"""Read-only Streamlit console for local EventAlpha state."""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import streamlit as st

from eventalpha.ui import StreamlitDataLoader, build_page_data
from eventalpha.ui.pages import (
    render_daily_briefing,
    render_dashboard,
    render_event_cards,
    render_footer,
    render_lifecycle,
    render_reviews,
    render_rule_updates,
    render_scheduler_status,
)


PAGES = [
    "Dashboard 首页",
    "每日简报",
    "事件卡片",
    "生命周期",
    "自动复盘",
    "规则更新",
    "调度器状态",
]


def main() -> None:
    """Run the Streamlit app."""
    demo_mode = _is_demo_mode()
    st.set_page_config(page_title="EventAlpha 投研 Agent 控制台", layout="wide")
    st.sidebar.title("EventAlpha")
    if demo_mode:
        st.sidebar.success("Demo mode: data/demo + reports/demo")
    page = st.sidebar.radio("页面", PAGES, index=0)
    selected_date = st.sidebar.date_input("简报日期", value=date.today())
    max_items = st.sidebar.number_input("本地读取上限", min_value=5, max_value=200, value=50, step=5)
    st.sidebar.caption("只读 · 离线 · 不调用 LLM · 不写 ledger · 不启动 scheduler daemon")

    loader = _build_loader(demo_mode=demo_mode, max_items=int(max_items))
    bundle = loader.load(briefing_date=selected_date)
    if demo_mode and not _has_demo_payload(bundle):
        st.info("请先运行 `python scripts/run_full_demo.py --reset-demo-state --write-summary` 生成本地 demo 数据。")
    page_data = build_page_data(bundle)

    if page == "Dashboard 首页":
        render_dashboard(st, page_data)
    elif page == "每日简报":
        render_daily_briefing(
            st,
            page_data,
            collected_data=bundle["collected_data"],
            selected_date=selected_date,
        )
    elif page == "事件卡片":
        render_event_cards(st, page_data)
    elif page == "生命周期":
        render_lifecycle(st, page_data)
    elif page == "自动复盘":
        render_reviews(st, page_data)
    elif page == "规则更新":
        render_rule_updates(st, page_data)
    elif page == "调度器状态":
        render_scheduler_status(st, page_data)

    render_footer(st)


def _is_demo_mode() -> bool:
    """Return True when the console should read isolated demo paths."""
    return "--demo-mode" in sys.argv or os.getenv("EVENTALPHA_DEMO_MODE", "").strip().casefold() in {
        "1",
        "true",
        "yes",
    }


def _build_loader(*, demo_mode: bool, max_items: int) -> StreamlitDataLoader:
    """Build the read-only data loader for normal or demo mode."""
    if not demo_mode:
        return StreamlitDataLoader(max_items=max_items)
    root = Path(__file__).resolve().parent
    return StreamlitDataLoader(
        reports_dir=root / "reports" / "demo",
        lifecycle_store_path=root / "data" / "demo" / "event_lifecycle_store.json",
        state_path=root / "data" / "demo" / "scheduler_state.json",
        runs_path=root / "data" / "demo" / "scheduler_runs.jsonl",
        ledger_path=root / "data" / "demo" / "eventalpha_demo.sqlite3",
        max_items=max_items,
    )


def _has_demo_payload(bundle: dict) -> bool:
    """Return True when demo mode has enough local data to display."""
    data = bundle.get("collected_data")
    return bool(
        bundle.get("reports")
        or (data and (data.event_cards or data.review_results or data.rule_updates or data.active_events))
    )


if __name__ == "__main__":
    main()
