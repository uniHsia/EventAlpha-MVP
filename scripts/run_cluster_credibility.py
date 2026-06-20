"""Run cluster-level multi-source credibility pre-verification."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.news import (  # noqa: E402
    ClusterCredibilityService,
    ClusterVerificationService,
    NewsClusterer,
    NewsKeywordFilter,
    NewsSourceRegistry,
    build_mock_registry,
    build_real_registry,
    deduplicate_news,
)
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402


def run_cluster_credibility(
    query: str | None = None,
    limit: int = 10,
    real_fetch: bool = False,
    source: str = "all",
    rss_feeds: list[str] | None = None,
    registry: NewsSourceRegistry | None = None,
) -> dict[str, Any]:
    """Fetch, cluster, and build credibility reports for candidate events."""
    selected_registry = registry or (
        build_real_registry(rss_feeds=rss_feeds, source=source) if real_fetch else build_mock_registry()
    )
    fetch_result = selected_registry.fetch_all(query=query, limit_per_source=limit)
    dedup_result = deduplicate_news(fetch_result.items)
    filter_result = NewsKeywordFilter().filter_items(dedup_result.items)
    clusterer = NewsClusterer()
    verifier = ClusterVerificationService()
    clusters = [verifier.verify(cluster) for cluster in clusterer.cluster(filter_result.candidates)]
    reports = [ClusterCredibilityService().evaluate(cluster) for cluster in clusters]
    return {
        "fetch_result": fetch_result,
        "dedup_result": dedup_result,
        "filter_result": filter_result,
        "clusters": clusters,
        "reports": reports,
    }


def _print_reports(result: dict[str, Any]) -> None:
    fetch_result = result["fetch_result"]
    dedup_result = result["dedup_result"]
    filter_result = result["filter_result"]
    clusters = result["clusters"]
    reports = {report.cluster_id: report for report in result["reports"]}

    print("EventAlpha-MVP Cluster Credibility")
    print(f"Fetched items: {len(fetch_result.items)}")
    print(f"Deduped items: {dedup_result.after_count} (duplicates={dedup_result.duplicate_count})")
    print(f"Candidate news items: {filter_result.after_count}")
    print(f"Credibility reports: {len(reports)}")
    if fetch_result.errors:
        print("\n## Source Errors")
        for error in fetch_result.errors:
            print(f"- {error}")

    print("\n## Cluster Credibility Reports")
    for index, cluster in enumerate(clusters, start=1):
        report = reports[cluster.cluster_id]
        print(f"{index}. {cluster.canonical_title}")
        print(f"   score={report.credibility_score:.2f} status={report.credibility_status}")
        print(f"   consistency={report.consistency_status} official={report.official_evidence_status}")
        print("   sources=" + "; ".join(
            f"{source.source_name}:{source.source_type}/{source.credibility_tier}"
            for source in report.source_summary
        ))
        print("   claims=" + " | ".join(f"{claim.claim_type}: {claim.claim_text}" for claim in report.claims))
        if report.risk_flags:
            print(f"   risk_flags={', '.join(report.risk_flags)}")
        if report.verification_notes:
            print(f"   notes={' | '.join(report.verification_notes)}")


def main() -> None:
    """Run cluster credibility CLI."""
    parser = ArgumentParser(description="Run EventAlpha cluster credibility pre-verification.")
    parser.add_argument("--query", default=None, help="Optional provider query.")
    parser.add_argument("--limit", type=int, default=10, help="Limit per source.")
    parser.add_argument("--real-fetch", action="store_true", help="Enable real GDELT/RSS network fetch.")
    parser.add_argument(
        "--source",
        default="all",
        choices=["all", "gdelt", "rss"],
        help="Real-fetch source selection. Use rss to skip GDELT rate limits.",
    )
    parser.add_argument("--rss-feed", action="append", default=None, help="RSS feed URL, repeatable.")
    args = parser.parse_args()

    result = run_cluster_credibility(
        query=args.query,
        limit=args.limit,
        real_fetch=args.real_fetch,
        source=args.source,
        rss_feeds=args.rss_feed,
    )
    _print_reports(result)
    print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
