"""Run EventAlpha event lifecycle tracking."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.news import (  # noqa: E402
    ClusterCredibilityService,
    ClusterVerificationService,
    DEFAULT_LIFECYCLE_STORE_PATH,
    EventLifecycleMatcher,
    EventLifecycleStore,
    EventLifecycleUpdater,
    NewsClusterer,
    NewsKeywordFilter,
    NewsSourceRegistry,
    TrackedEvent,
    build_mock_registry,
    build_real_registry,
    deduplicate_news,
)
from eventalpha.orchestration import run_event_pipeline  # noqa: E402
from eventalpha.schemas import RISK_DISCLAIMER, RawNews  # noqa: E402


def run_event_lifecycle_tracker(
    query: str | None = None,
    limit: int = 10,
    real_fetch: bool = False,
    source: str = "all",
    rss_feeds: list[str] | None = None,
    store_path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH,
    reset_store: bool = False,
    list_active: bool = False,
    analyze_updated: int = 0,
    registry: NewsSourceRegistry | None = None,
) -> dict[str, Any]:
    """Fetch clusters, update lifecycle store, and optionally analyze updated events."""
    store = EventLifecycleStore(store_path).load()
    if reset_store:
        store.reset()

    if list_active:
        return {
            "store": store,
            "active_events": store.list_active_events(),
            "updates": [],
            "stale_updates": [],
            "analyses": [],
            "fetch_result": None,
            "dedup_result": None,
            "filter_result": None,
            "clusters": [],
            "reports": {},
            "match_results": [],
        }

    selected_registry = registry or (
        build_real_registry(rss_feeds=rss_feeds, source=source) if real_fetch else build_mock_registry()
    )
    fetch_result = selected_registry.fetch_all(query=query, limit_per_source=limit)
    dedup_result = deduplicate_news(fetch_result.items)
    filter_result = NewsKeywordFilter().filter_items(dedup_result.items)
    clusterer = NewsClusterer()
    verifier = ClusterVerificationService()
    clusters = [verifier.verify(cluster) for cluster in clusterer.cluster(filter_result.candidates)]
    credibility_service = ClusterCredibilityService()
    reports = {cluster.cluster_id: credibility_service.evaluate(cluster) for cluster in clusters}

    matcher = EventLifecycleMatcher()
    updater = EventLifecycleUpdater()
    updates = []
    match_results = []
    for cluster in clusters:
        existing_events = store.list_events()
        report = reports[cluster.cluster_id]
        match = matcher.match(cluster, report, existing_events)
        match_results.append(match)
        matched_event = store.get(match.tracked_event_id) if match.matched and match.tracked_event_id else None
        event, event_updates = updater.apply(cluster, report, matched_event=matched_event)
        store.upsert(event)
        updates.extend(event_updates)

    stale_updates = updater.mark_stale(store.list_events())
    store.save()
    analyses = _analyze_updated_events(store, updates, analyze_updated)

    return {
        "store": store,
        "active_events": store.list_active_events(),
        "updates": updates,
        "stale_updates": stale_updates,
        "analyses": analyses,
        "fetch_result": fetch_result,
        "dedup_result": dedup_result,
        "filter_result": filter_result,
        "clusters": clusters,
        "reports": reports,
        "match_results": match_results,
    }


def _analyze_updated_events(
    store: EventLifecycleStore,
    updates: list[Any],
    analyze_updated: int,
) -> list[dict[str, Any]]:
    if analyze_updated <= 0:
        return []
    update_counts = Counter(update.tracked_event_id for update in updates)
    candidates = sorted(
        store.list_active_events(),
        key=lambda event: (update_counts[event.tracked_event_id], event.last_seen_at),
        reverse=True,
    )
    analyses = []
    for event in candidates[:analyze_updated]:
        raw_news = _tracked_event_to_raw_news(event)
        pipeline_result = run_event_pipeline(raw_news, persist=False)
        analyses.append({"tracked_event": event, "raw_news": raw_news, "pipeline_result": pipeline_result})
    return analyses


def _tracked_event_to_raw_news(event: TrackedEvent) -> RawNews:
    raw_text = event.current_summary or "\n".join(event.latest_claims[:3]) or event.canonical_title
    metadata = {
        "tracked_event_id": event.tracked_event_id,
        "event_key": event.event_key,
        "lifecycle_stage": event.lifecycle_stage,
        "source_count": str(event.source_count),
        "cluster_ids": "|".join(event.cluster_ids),
        "credibility_status": event.credibility_status or "",
        "official_evidence_status": event.official_evidence_status or "",
        "dominant_keywords": ",".join(event.dominant_keywords),
    }
    return RawNews(
        raw_id=event.tracked_event_id,
        title=event.canonical_title,
        source=", ".join(event.sources[:5]) or "event_lifecycle",
        source_type="unknown",
        publish_time=event.last_seen_at,
        raw_text=raw_text,
        metadata=metadata,
    )


def _print_result(result: dict[str, Any]) -> None:
    print("EventAlpha-MVP Event Lifecycle Tracker")
    fetch_result = result.get("fetch_result")
    dedup_result = result.get("dedup_result")
    filter_result = result.get("filter_result")
    if fetch_result is not None:
        print(f"Fetched items: {len(fetch_result.items)}")
        print(f"Deduped items: {dedup_result.after_count} (duplicates={dedup_result.duplicate_count})")
        print(f"Candidate news items: {filter_result.after_count}")
        print(f"Clusters processed: {len(result['clusters'])}")
        if fetch_result.errors:
            print("\n## Source Errors")
            for error in fetch_result.errors:
                print(f"- {error}")

    updates = result["updates"] + result["stale_updates"]
    print(f"Lifecycle updates: {len(updates)}")
    if updates:
        print("\n## Updates")
        for update in updates:
            stage = f"{update.old_stage}->{update.new_stage}" if update.old_stage != update.new_stage else update.new_stage
            print(f"- {update.update_type}: {update.tracked_event_id} ({stage})")
            if update.notes:
                print(f"  notes={' | '.join(update.notes)}")

    print("\n## Active Events")
    for event in result["active_events"]:
        print(
            f"- {event.tracked_event_id} [{event.lifecycle_stage}] "
            f"{event.canonical_title} sources={event.source_count} "
            f"credibility={event.credibility_status or 'unknown'}"
        )
        if event.timeline:
            latest = event.timeline[-1]
            print(f"  latest={latest.update_type} at {latest.timestamp.isoformat()}")

    if result["analyses"]:
        print("\n## Event Pipeline Analysis")
        for index, analysis in enumerate(result["analyses"], start=1):
            event = analysis["tracked_event"]
            print(f"\n### Analysis {index}: {event.canonical_title}")
            print(json.dumps(analysis["pipeline_result"]["event_card"].model_dump(mode="json"), ensure_ascii=False, indent=2))


def main() -> None:
    """Run the lifecycle tracker CLI."""
    parser = ArgumentParser(description="Track event lifecycle state from news clusters.")
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
    parser.add_argument("--store-path", default=str(DEFAULT_LIFECYCLE_STORE_PATH), help="Lifecycle JSON store path.")
    parser.add_argument("--reset-store", action="store_true", help="Clear the lifecycle store before running.")
    parser.add_argument("--list-active", action="store_true", help="List active events without fetching news.")
    parser.add_argument("--analyze-updated", type=int, default=0, help="Analyze top N updated events with EventAlpha.")
    args = parser.parse_args()

    result = run_event_lifecycle_tracker(
        query=args.query,
        limit=args.limit,
        real_fetch=args.real_fetch,
        source=args.source,
        rss_feeds=args.rss_feed,
        store_path=args.store_path,
        reset_store=args.reset_store,
        list_active=args.list_active,
        analyze_updated=args.analyze_updated,
    )
    _print_result(result)
    print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
