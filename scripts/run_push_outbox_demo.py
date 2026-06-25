"""Generate a local push outbox from EventCards and demo subscribers."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.notification import build_push_message, load_subscribers, match_event_to_subscribers, write_push_outbox  # noqa: E402
from eventalpha.ui.components import build_page_data  # noqa: E402
from eventalpha.ui.data_loader import StreamlitDataLoader  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Generate EventAlpha push outbox demo.")
    parser.add_argument("--demo-mode", action="store_true")
    parser.add_argument("--subscribers", default=None, help="Subscriber JSON path.")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD report date.")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date) if args.date else date.today()
    reports_dir = ROOT / "reports" / "demo" if args.demo_mode else ROOT / "reports"
    subscriber_path = Path(args.subscribers) if args.subscribers else ROOT / "data" / "subscribers.demo.json"
    subscribers = load_subscribers(subscriber_path)
    page_data = _load_page_data(args.demo_mode, report_date)
    messages = []
    for event_card in page_data.event_cards:
        for subscriber, reason in match_event_to_subscribers(event_card, subscribers):
            messages.append(build_push_message(event_card, subscriber, reason=reason))
    paths = write_push_outbox(messages, reports_dir=reports_dir, report_date=report_date, demo_mode=args.demo_mode)
    print("Push outbox written")
    print("微信通道当前为 placeholder，已完成订阅匹配与推送消息生成。")
    print(f"Messages: {len(messages)}")
    print(f"Markdown: {paths['markdown']}")
    print(f"JSON: {paths['json']}")


def _load_page_data(demo_mode: bool, report_date: date):
    if not demo_mode:
        return build_page_data(StreamlitDataLoader(max_items=100).load(briefing_date=report_date))
    loader = StreamlitDataLoader(
        reports_dir=ROOT / "reports" / "demo",
        lifecycle_store_path=ROOT / "data" / "demo" / "event_lifecycle_store.json",
        state_path=ROOT / "data" / "demo" / "scheduler_state.json",
        runs_path=ROOT / "data" / "demo" / "scheduler_runs.jsonl",
        ledger_path=ROOT / "data" / "demo" / "eventalpha_demo.sqlite3",
        historical_cases_path=ROOT / "data" / "demo" / "historical_cases.json",
        max_items=100,
        source_kind="demo",
        source_label="本地 Demo 数据",
    )
    return build_page_data(loader.load(briefing_date=report_date))


if __name__ == "__main__":
    main()
