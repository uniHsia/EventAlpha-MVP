"""Check asset proxy mapping coverage for bundled demo events."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents import extract_event, map_event_to_markets
from eventalpha.data_sources import ProviderRouter
from eventalpha.schemas import CausalChain, RawNews, RISK_DISCLAIMER


def build_coverage_report(
    demo_path: str | Path = ROOT / "eventalpha" / "examples" / "demo_events.json",
    router: ProviderRouter | None = None,
) -> dict[str, Any]:
    """Build a non-network asset coverage report for demo events."""
    router = router or ProviderRouter()
    demo_events = json.loads(Path(demo_path).read_text(encoding="utf-8"))
    event_reports = []
    totals = {
        "total_assets": 0,
        "verified_count": 0,
        "candidate_count": 0,
        "unverified_count": 0,
        "missing_count": 0,
        "csv_count": 0,
        "akshare_count": 0,
        "mock_count": 0,
        "live_ok_count": 0,
        "live_failed_count": 0,
        "cache_only_count": 0,
        "not_checked_count": 0,
        "fallback_available_count": 0,
        "fully_reviewable_count": 0,
        "reviewable_with_candidate_count": 0,
        "missing_or_unverified_count": 0,
    }

    for item in demo_events:
        raw_news = RawNews(**item)
        event = extract_event(raw_news)
        chain = CausalChain(event_id=event.event_id, confidence=0.5)
        market_mapping = map_event_to_markets(event, chain)
        asset_names = [asset.asset_name for asset in market_mapping.mapped_assets]
        rule = router.proxy_rules.get(event.event_type)
        if rule:
            for candidate in rule.candidates:
                if candidate.asset_name not in asset_names:
                    asset_names.append(candidate.asset_name)

        assets = []
        for asset_name in asset_names:
            coverage = router.get_asset_coverage(asset_name, event.event_type)
            assets.append(coverage)
            totals["total_assets"] += 1
            totals[f"{coverage.mapping_status}_count"] = (
                totals.get(f"{coverage.mapping_status}_count", 0) + 1
            )
            if coverage.provider in {"csv", "akshare", "mock"}:
                totals[f"{coverage.provider}_count"] = (
                    totals.get(f"{coverage.provider}_count", 0) + 1
                )
            totals[f"{coverage.validation_status}_count"] = (
                totals.get(f"{coverage.validation_status}_count", 0) + 1
            )
            if coverage.fallback_available:
                totals["fallback_available_count"] += 1
            if (
                coverage.is_usable
                and coverage.mapping_status == "verified"
                and coverage.validation_status in {"live_ok", "cache_only"}
            ):
                totals["fully_reviewable_count"] += 1
            if coverage.is_usable and coverage.mapping_status == "candidate":
                totals["reviewable_with_candidate_count"] += 1
            if coverage.mapping_status in {"missing", "unverified"} or not coverage.is_usable:
                totals["missing_or_unverified_count"] += 1

        event_reports.append(
            {
                "event_title": event.event_title,
                "event_type": event.event_type,
                "assets": assets,
            }
        )

    covered = (
        totals["verified_count"]
        + totals["candidate_count"]
        + totals["unverified_count"]
    )
    totals["coverage_rate"] = (
        round(covered / totals["total_assets"], 4) if totals["total_assets"] else 0.0
    )
    return {"events": event_reports, "summary": totals}


def print_coverage_report(report: dict[str, Any]) -> None:
    """Print a readable coverage report."""
    for event_report in report["events"]:
        print(f"\nevent_type: {event_report['event_type']}")
        print(f"event_title: {event_report['event_title']}")
        for coverage in event_report["assets"]:
            fallback_text = ", ".join(
                f"{route.proxy_asset_name}/{route.provider}/{route.mapping_status}/{route.validation_status}"
                for route in coverage.fallback_routes
            ) or "none"
            print(
                "资产: "
                f"{coverage.asset_name} -> "
                f"primary={coverage.proxy_asset_name}/{coverage.provider}, "
                f"status={coverage.mapping_status}/{coverage.validation_status}, "
                f"fallbacks=[{fallback_text}], "
                f"source={coverage.route_source}, "
                f"usable={coverage.is_usable}"
            )
            if coverage.reason:
                print(f"  reason: {coverage.reason}")

    print("\nsummary:")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    print(RISK_DISCLAIMER)


def main() -> None:
    """Run coverage report from the command line."""
    parser = ArgumentParser(description="Check EventAlpha asset proxy coverage.")
    parser.add_argument(
        "--demo-path",
        default=str(ROOT / "eventalpha" / "examples" / "demo_events.json"),
        help="Path to demo_events.json.",
    )
    args = parser.parse_args()

    print_coverage_report(build_coverage_report(args.demo_path))


if __name__ == "__main__":
    main()
