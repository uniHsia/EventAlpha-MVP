"""Read-only Streamlit console for local EventAlpha state."""

from __future__ import annotations

import os
import sys
import importlib
import inspect
from datetime import date, datetime
from pathlib import Path

import streamlit as st

import eventalpha.ui.components as ui_components
import eventalpha.ui.data_loader as ui_data_loader
import eventalpha.ui.formatters as ui_formatters
import eventalpha.ui.pages as ui_pages

# Streamlit reruns the app in one Python process. Reload UI modules so the app
# cannot run with a new app_streamlit.py and stale page/data-loader signatures.
ui_formatters = importlib.reload(ui_formatters)
ui_components = importlib.reload(ui_components)
ui_data_loader = importlib.reload(ui_data_loader)
ui_pages = importlib.reload(ui_pages)

StreamlitDataLoader = ui_data_loader.StreamlitDataLoader
build_page_data = ui_components.build_page_data


PAGES = [
    "首页总览",
    "事件中心",
    "每日简报",
    "预测账本",
    "自动复盘",
    "规则更新",
    "生命周期",
    "历史案例",
    "系统设置",
    "调度器状态",
]


def main() -> None:
    """Run the Streamlit app."""
    demo_mode = _is_demo_mode()
    st.set_page_config(page_title="EventAlpha 投研 Agent 控制台", layout="wide")
    _render_global_shell_css()
    _render_sidebar_brand(demo_mode)
    if demo_mode:
        st.sidebar.success("Demo mode: data/demo + reports/demo")
    _sync_query_page()
    if "selected_page" not in st.session_state or st.session_state["selected_page"] not in PAGES:
        st.session_state["selected_page"] = PAGES[0]
    page = st.sidebar.radio(
        "页面",
        PAGES,
        index=PAGES.index(st.session_state["selected_page"]),
    )
    st.session_state["selected_page"] = page
    selected_date = st.sidebar.date_input("简报日期", value=date.today())
    max_items = st.sidebar.number_input("本地读取上限", min_value=5, max_value=200, value=50, step=5)
    st.sidebar.caption("只读 · 离线 · 不调用 LLM · 不写 ledger · 不启动 scheduler daemon")
    _render_sidebar_demo_card(demo_mode)

    loader = _build_loader(demo_mode=demo_mode, max_items=int(max_items))
    bundle = loader.load(briefing_date=selected_date)
    bundle.setdefault("source_kind", "demo" if demo_mode else "real")
    bundle.setdefault("source_label", "本地 Demo 数据" if demo_mode else "本地落盘数据")
    if demo_mode and not _has_demo_payload(bundle):
        st.info("请先运行 `python scripts/run_full_demo.py --reset-demo-state --write-summary` 生成本地 demo 数据。")
    page_data = build_page_data(bundle)

    if page == "首页总览":
        search_query = _render_home_toolbar()
        _render_page("render_dashboard", st, page_data, search_query=search_query)
    elif page == "事件中心":
        _render_page("render_event_cards", st, page_data)
    elif page == "每日简报":
        _render_page(
            "render_daily_briefing",
            st,
            page_data,
            collected_data=bundle["collected_data"],
            selected_date=selected_date,
        )
    elif page == "预测账本":
        _render_prediction_ledger_page(st, page_data)
    elif page == "自动复盘":
        _render_page("render_reviews", st, page_data)
    elif page == "规则更新":
        _render_page("render_rule_updates", st, page_data)
    elif page == "生命周期":
        _render_page("render_lifecycle", st, page_data)
    elif page == "历史案例":
        _render_page("render_historical_cases", st, page_data)
    elif page == "系统设置":
        _render_page("render_system_status", st, page_data)
    elif page == "调度器状态":
        _render_page("render_scheduler_status", st, page_data)

    _render_page("render_footer", st)


def _is_demo_mode() -> bool:
    """Return True when the console should read isolated demo paths."""
    return "--demo-mode" in sys.argv or os.getenv("EVENTALPHA_DEMO_MODE", "").strip().casefold() in {
        "1",
        "true",
        "yes",
    }


def _render_sidebar_brand(demo_mode: bool) -> None:
    """Render a compact product brand block in the sidebar."""
    st.sidebar.markdown(
        f"""
<div style="padding:8px 2px 18px;">
  <div style="display:flex;align-items:center;gap:10px;">
    <div style="width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#18dcff,#0b72ff);display:grid;place-items:center;color:white;font-weight:900;box-shadow:0 10px 24px rgba(12,119,255,.35);">E</div>
    <div>
      <div style="font-size:20px;font-weight:900;line-height:1.05;">EventAlpha</div>
      <div style="font-size:12px;color:rgba(237,245,255,.72);margin-top:4px;">热点事件驱动投资研究 Agent</div>
    </div>
  </div>
  <div style="height:1px;background:rgba(255,255,255,.1);margin-top:16px;"></div>
  <div style="font-size:12px;color:rgba(237,245,255,.7);margin-top:10px;">{"Demo 工作台" if demo_mode else "本地研究控制台"}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_global_shell_css() -> None:
    """Hide default Streamlit chrome and keep the product sidebar compact."""
    st.markdown(
        """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
section[data-testid="stSidebar"] {
  min-width: 232px !important;
  max-width: 240px !important;
}
div.block-container {
  padding-top: 0.75rem;
}
.ea-st-toolbar {
  margin: -0.2rem 0 0.85rem;
}
div[data-testid="stTextInput"] input {
  border-radius: 9px;
  border-color: #d6e2f3;
  min-height: 42px;
}
div[data-testid="stButton"] button {
  border-radius: 9px;
  min-height: 40px;
  font-weight: 800;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _render_sidebar_demo_card(demo_mode: bool) -> None:
    """Render the visual demo card shown near the sidebar bottom."""
    label = "一键演示已启用" if demo_mode else "本地只读模式"
    st.sidebar.markdown(
        f"""
<div style="margin-top:18px;border:1px solid rgba(110,171,255,.28);border-radius:10px;padding:16px;background:linear-gradient(180deg,rgba(11,79,176,.55),rgba(4,24,65,.72));box-shadow:0 18px 36px rgba(0,0,0,.18);">
  <div style="font-size:17px;font-weight:900;margin-bottom:8px;">Demo Mode</div>
  <div style="font-size:12px;line-height:1.7;color:rgba(237,245,255,.78);">本地演示数据<br/>Mock + RSS + CSV</div>
  <div style="height:112px;margin:14px 0;border-radius:10px;background:radial-gradient(circle at 50% 35%,rgba(62,191,255,.85),rgba(16,91,236,.28) 32%,transparent 33%),linear-gradient(135deg,rgba(22,107,255,.32),rgba(4,18,48,.9));border:1px solid rgba(130,190,255,.18);"></div>
  <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:rgba(237,245,255,.86);"><span style="width:7px;height:7px;border-radius:50%;background:#17d59a;display:inline-block;"></span>{label}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_home_toolbar() -> str:
    """Render the product toolbar above the dashboard and return search text."""
    st.markdown('<div class="ea-st-toolbar">', unsafe_allow_html=True)
    cols = st.columns([5.2, 1.35, 1.7, 0.42], vertical_alignment="center")
    search_query = cols[0].text_input(
        "本地搜索",
        "",
        placeholder="搜索已加载的 EventCard / Ledger / ReviewResult / RuleUpdate",
        label_visibility="collapsed",
    )
    if cols[1].button("查看今日简报", use_container_width=True, key="home_toolbar_briefing"):
        st.session_state["selected_page"] = "每日简报"
        st.rerun()
    cols[2].caption(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
    if cols[3].button("i", use_container_width=True, key="home_toolbar_info"):
        st.toast("本页只展示本地已加载数据；Demo / 待接入状态均已标注。")
    st.markdown("</div>", unsafe_allow_html=True)
    return search_query


def _render_prediction_ledger_page(st, page_data) -> None:
    """Render ledger page even if Streamlit is holding an older pages module."""
    renderer = getattr(ui_pages, "render_prediction_ledger", None)
    if renderer is not None:
        renderer(st, page_data)
        return

    st.title("预测账本")
    st.caption("仅展示本地 Prediction Ledger / predicted_assets 已记录字段；缺失字段不补造。")
    rows = page_data.prediction_ledger_rows
    query = st.text_input("文本搜索", "", placeholder="搜索事件、资产、PredictionID")
    if query:
        needle = query.casefold()
        rows = [row for row in rows if needle in str(row).casefold()]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("暂无 Prediction Ledger 记录。")


def _render_page(function_name: str, *args, **kwargs) -> None:
    """Call a UI page renderer while tolerating older hot-reloaded signatures."""
    renderer = getattr(ui_pages, function_name, None)
    if renderer is None:
        st.error(f"页面函数 {function_name} 未加载，请重启 Streamlit。")
        return

    signature = inspect.signature(renderer)
    accepted_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters
        or any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())
    }
    renderer(*args, **accepted_kwargs)


def _build_loader(*, demo_mode: bool, max_items: int) -> StreamlitDataLoader:
    """Build the read-only data loader for normal or demo mode."""
    if not demo_mode:
        loader = StreamlitDataLoader(max_items=max_items)
        return _mark_loader_source(loader, source_kind="real", source_label="本地落盘数据")
    root = Path(__file__).resolve().parent
    loader = StreamlitDataLoader(
        reports_dir=root / "reports" / "demo",
        lifecycle_store_path=root / "data" / "demo" / "event_lifecycle_store.json",
        state_path=root / "data" / "demo" / "scheduler_state.json",
        runs_path=root / "data" / "demo" / "scheduler_runs.jsonl",
        ledger_path=root / "data" / "demo" / "eventalpha_demo.sqlite3",
        historical_cases_path=root / "data" / "demo" / "historical_cases.json",
        max_items=max_items,
    )
    return _mark_loader_source(loader, source_kind="demo", source_label="本地 Demo 数据")


def _mark_loader_source(
    loader: StreamlitDataLoader,
    *,
    source_kind: str,
    source_label: str,
) -> StreamlitDataLoader:
    """Set UI provenance without relying on constructor support in hot-reload sessions."""
    setattr(loader, "source_kind", source_kind)
    setattr(loader, "source_label", source_label)
    return loader


def _sync_query_page() -> None:
    """Apply lightweight module links such as ?page=预测账本."""
    try:
        query_page = st.query_params.get("page")
    except Exception:
        query_page = None
    if isinstance(query_page, list):
        query_page = query_page[0] if query_page else None
    if query_page in PAGES:
        st.session_state["selected_page"] = query_page
        try:
            del st.query_params["page"]
        except Exception:
            pass


def _has_demo_payload(bundle: dict) -> bool:
    """Return True when demo mode has enough local data to display."""
    data = bundle.get("collected_data")
    return bool(
        bundle.get("reports")
        or (data and (data.event_cards or data.review_results or data.rule_updates or data.active_events))
    )


if __name__ == "__main__":
    main()
