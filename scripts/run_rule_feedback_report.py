"""Generate local rule feedback signals from ReviewResult and RuleUpdate rows."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.learning import load_rule_feedback_signals, write_rule_feedback_report  # noqa: E402
from eventalpha.ui.components import build_page_data  # noqa: E402
from eventalpha.ui.data_loader import StreamlitDataLoader  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Generate EventAlpha rule feedback signals.")
    parser.add_argument("--demo-mode", action="store_true")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD report date.")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date) if args.date else date.today()
    reports_dir = ROOT / "reports" / "demo" if args.demo_mode else ROOT / "reports"
    page_data = _load_page_data(args.demo_mode, report_date)
    signals = load_rule_feedback_signals(
        review_results=page_data.review_results,
        rule_updates=page_data.rule_updates,
        ledger_rows=page_data.prediction_ledger_rows,
    )
    paths = write_rule_feedback_report(signals, reports_dir=reports_dir, report_date=report_date, demo_mode=args.demo_mode)
    print("Rule feedback report written")
    print(f"Signals: {len(signals)}")
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
