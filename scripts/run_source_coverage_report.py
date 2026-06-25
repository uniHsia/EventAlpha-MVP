"""Generate a local source coverage report."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.news.source_coverage import collect_source_coverage, write_source_coverage_report  # noqa: E402


def main() -> None:
    parser = ArgumentParser(description="Generate EventAlpha source coverage report.")
    parser.add_argument("--demo-mode", action="store_true")
    parser.add_argument("--real-fetch", action="store_true", help="Opt in to real RSS/GDELT checks.")
    parser.add_argument("--source", default="all", choices=["all", "gdelt", "rss"])
    parser.add_argument("--rss-feed", action="append", default=None)
    parser.add_argument("--query", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD report date.")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date) if args.date else date.today()
    reports_dir = ROOT / "reports" / "demo" if args.demo_mode else ROOT / "reports"
    report = collect_source_coverage(
        real_fetch=args.real_fetch,
        source=args.source,
        rss_feeds=args.rss_feed,
        query=args.query,
        limit=args.limit,
        demo_mode=args.demo_mode,
    )
    paths = write_source_coverage_report(report, reports_dir=reports_dir, report_date=report_date)
    print("Source coverage report written")
    print(f"Markdown: {paths['markdown']}")
    print(f"JSON: {paths['json']}")


if __name__ == "__main__":
    main()
