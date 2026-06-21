"""Read-only Streamlit console for local EventAlpha state."""

from __future__ import annotations

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
    "Dashboard",
    "Daily Briefing",
    "Event Cards",
    "Lifecycle",
    "Reviews",
    "Rule Updates",
    "Scheduler Status",
]


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(page_title="EventAlpha Console", layout="wide")
    st.sidebar.title("EventAlpha")
    page = st.sidebar.radio("页面", PAGES, index=0)
    selected_date = st.sidebar.date_input("Briefing date", value=date.today())
    max_items = st.sidebar.number_input("Max local rows", min_value=5, max_value=200, value=50, step=5)
    st.sidebar.caption("只读 · 离线 · 不调用 LLM · 不写 ledger · 不启动 scheduler daemon")

    loader = StreamlitDataLoader(max_items=int(max_items))
    bundle = loader.load(briefing_date=selected_date)
    page_data = build_page_data(bundle)

    if page == "Dashboard":
        render_dashboard(st, page_data)
    elif page == "Daily Briefing":
        render_daily_briefing(
            st,
            page_data,
            collected_data=bundle["collected_data"],
            selected_date=selected_date,
        )
    elif page == "Event Cards":
        render_event_cards(st, page_data)
    elif page == "Lifecycle":
        render_lifecycle(st, page_data)
    elif page == "Reviews":
        render_reviews(st, page_data)
    elif page == "Rule Updates":
        render_rule_updates(st, page_data)
    elif page == "Scheduler Status":
        render_scheduler_status(st, page_data)

    render_footer(st)


if __name__ == "__main__":
    main()
