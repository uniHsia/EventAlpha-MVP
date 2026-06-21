"""Build an offline EventAlpha daily briefing."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.briefing import (  # noqa: E402
    BriefingDataCollector,
    DailyBriefingBuilder,
    JSONBriefingWriter,
    MarkdownBriefingRenderer,
)


def build_daily_briefing(
    *,
    briefing_date: date | None = None,
    max_items: int = 10,
    write_report: bool = False,
    reports_dir: str | Path = "reports",
    state_path: str | Path = "data/scheduler_state.json",
    runs_path: str | Path = "data/scheduler_runs.jsonl",
    ledger_path: str | Path | None = None,
    lifecycle_store_path: str | Path = "data/event_lifecycle_store.json",
) -> dict[str, Any]:
    """Build one briefing and optionally write report files."""
    target_date = briefing_date or date.today()
    data = BriefingDataCollector(
        lifecycle_store_path=lifecycle_store_path,
        state_path=state_path,
        runs_path=runs_path,
        ledger_path=ledger_path,
        max_items=max_items,
    ).collect(target_date)
    briefing = DailyBriefingBuilder(max_items=max_items).build(data)
    markdown = MarkdownBriefingRenderer().render(briefing)
    paths = None
    if write_report:
        paths = JSONBriefingWriter(reports_dir).write(briefing, markdown=markdown)
    return {
        "collected_data": data,
        "briefing": briefing,
        "markdown": markdown,
        "paths": paths,
    }


def main(argv: list[str] | None = None) -> None:
    """Run the daily briefing CLI."""
    parser = ArgumentParser(description="Build an offline EventAlpha daily briefing.")
    parser.add_argument("--write-report", action="store_true", help="Write Markdown and JSON files.")
    parser.add_argument("--date", dest="briefing_date", default=None, help="Briefing date in YYYY-MM-DD format.")
    parser.add_argument("--max-items", type=int, default=10, help="Maximum items per section.")
    parser.add_argument("--reports-dir", default="reports", help="Report output directory.")
    parser.add_argument("--state-path", default="data/scheduler_state.json", help="Scheduler state JSON path.")
    parser.add_argument("--runs-path", default="data/scheduler_runs.jsonl", help="Scheduler runs JSONL path.")
    parser.add_argument("--ledger-path", default=None, help="Optional SQLite ledger path.")
    parser.add_argument("--lifecycle-store-path", default="data/event_lifecycle_store.json", help="Lifecycle store path.")
    args = parser.parse_args(argv)

    target_date = date.fromisoformat(args.briefing_date) if args.briefing_date else None
    result = build_daily_briefing(
        briefing_date=target_date,
        max_items=args.max_items,
        write_report=args.write_report,
        reports_dir=args.reports_dir,
        state_path=args.state_path,
        runs_path=args.runs_path,
        ledger_path=args.ledger_path,
        lifecycle_store_path=args.lifecycle_store_path,
    )
    print(result["markdown"])
    if result["paths"]:
        print("Report files written:")
        print(f"- Markdown: {result['paths']['markdown']}")
        print(f"- JSON: {result['paths']['json']}")


if __name__ == "__main__":
    main()
