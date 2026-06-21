"""Scheduler job runners for periodic EventAlpha scans."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from eventalpha.news import (
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
from eventalpha.orchestration import run_event_pipeline as default_run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.schemas.base import utc_now

from .schemas import SchedulerJobConfig, SchedulerRunRecord
from .state_store import SchedulerStateStore


def run_news_lifecycle_scan(
    config: SchedulerJobConfig,
    store: SchedulerStateStore,
    *,
    lifecycle_store_path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH,
    registry: NewsSourceRegistry | None = None,
) -> SchedulerRunRecord:
    """Fetch, cluster, and update event lifecycle state."""
    record = _started_record(config)
    try:
        lifecycle_store = EventLifecycleStore(lifecycle_store_path).load()
        scan = _scan_clusters(config, registry=registry)
        updates, stale_updates = _apply_lifecycle_updates(
            lifecycle_store=lifecycle_store,
            clusters=scan["clusters"],
            reports=scan["reports"],
        )
        record = record.model_copy(
            update={
                "fetched_items": len(scan["fetch_result"].items),
                "candidate_items": scan["filter_result"].after_count,
                "clusters_processed": len(scan["clusters"]),
                "lifecycle_updates": len(updates) + len(stale_updates),
                "errors": list(scan["fetch_result"].errors),
                "notes": _scan_notes(config),
            }
        )
        if config.dry_run:
            record = record.finish("dry_run", notes=record.notes + ["Dry-run: lifecycle store was not saved."])
        else:
            lifecycle_store.save()
            record = record.finish("success")
    except Exception as exc:  # pragma: no cover - defensive job boundary
        record = record.finish("failed", errors=record.errors + [str(exc)])
    store.append_run(record)
    return record


def run_candidate_analysis(
    config: SchedulerJobConfig,
    store: SchedulerStateStore,
    *,
    lifecycle_store_path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH,
    pipeline_runner: Callable[..., dict[str, Any]] = default_run_event_pipeline,
    extraction_agent: Any | None = None,
    causal_agent: Any | None = None,
    anti_spurious_agent: Any | None = None,
) -> SchedulerRunRecord:
    """Analyze active lifecycle events with the existing event pipeline."""
    record = _started_record(config)
    try:
        lifecycle_store = EventLifecycleStore(lifecycle_store_path).load()
        active_events = lifecycle_store.list_active_events()
        candidates = active_events[: config.limit]
        notes = [f"Active events available: {len(active_events)}."]
        if config.dry_run:
            notes.extend(f"Would analyze: {event.canonical_title}" for event in candidates)
            record = record.model_copy(
                update={
                    "candidate_items": len(candidates),
                    "notes": notes + ["Dry-run: event pipeline was not called."],
                }
            ).finish("dry_run")
        else:
            analyses = []
            for event in candidates:
                raw_news = tracked_event_to_raw_news(event)
                analyses.append(
                    pipeline_runner(
                        raw_news,
                        persist=config.persist,
                        extraction_agent=extraction_agent,
                        causal_agent=causal_agent,
                        anti_spurious_agent=anti_spurious_agent,
                    )
                )
            if config.persist:
                notes.append("Persist=True was explicitly enabled for candidate analysis.")
            else:
                notes.append("Persist=False: Prediction Ledger was not written.")
            record = record.model_copy(
                update={
                    "candidate_items": len(candidates),
                    "analyzed_events": len(analyses),
                    "notes": notes,
                }
            ).finish("success")
    except Exception as exc:  # pragma: no cover - defensive job boundary
        record = record.finish("failed", errors=record.errors + [str(exc)])
    store.append_run(record)
    return record


def run_scheduler_status(
    config: SchedulerJobConfig,
    store: SchedulerStateStore,
    *,
    lifecycle_store_path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH,
) -> SchedulerRunRecord:
    """Report scheduler config, recent runs, and active lifecycle event counts."""
    record = _started_record(config)
    try:
        jobs = store.load_config()
        recent_runs = store.list_recent_runs(limit=10)
        active_events = EventLifecycleStore(lifecycle_store_path).load().list_active_events()
        errors = [error for run in recent_runs for error in run.errors]
        notes = [
            f"Configured jobs: {len(jobs)}.",
            f"Recent runs: {len(recent_runs)}.",
            f"Active events: {len(active_events)}.",
        ]
        for job in jobs:
            last_success = store.get_last_successful_run(job.job_id)
            if last_success:
                notes.append(f"Last successful {job.job_id}: {last_success.finished_at or last_success.started_at}.")
        record = record.model_copy(
            update={
                "candidate_items": len(active_events),
                "errors": errors[:10],
                "notes": notes,
            }
        ).finish("success")
    except Exception as exc:  # pragma: no cover - defensive job boundary
        record = record.finish("failed", errors=record.errors + [str(exc)])
    store.append_run(record)
    return record


def tracked_event_to_raw_news(event: TrackedEvent) -> RawNews:
    """Convert a tracked lifecycle event into RawNews for pipeline analysis."""
    raw_text = event.current_summary or "\n".join(event.latest_claims[:3]) or event.canonical_title
    return RawNews(
        raw_id=event.tracked_event_id,
        title=event.canonical_title,
        source=", ".join(event.sources[:5]) or "event_lifecycle",
        source_type="unknown",
        publish_time=event.last_seen_at,
        raw_text=raw_text,
        metadata={
            "tracked_event_id": event.tracked_event_id,
            "event_key": event.event_key,
            "lifecycle_stage": event.lifecycle_stage,
            "source_count": str(event.source_count),
        },
    )


def _scan_clusters(
    config: SchedulerJobConfig,
    *,
    registry: NewsSourceRegistry | None = None,
) -> dict[str, Any]:
    selected_registry = registry or (
        build_real_registry(
            rss_feeds=[config.rss_feed] if config.rss_feed else None,
            source=config.source,
        )
        if config.real_fetch
        else build_mock_registry()
    )
    fetch_result = selected_registry.fetch_all(query=config.query, limit_per_source=config.limit)
    dedup_result = deduplicate_news(fetch_result.items)
    filter_result = NewsKeywordFilter().filter_items(dedup_result.items)
    clusters = [
        ClusterVerificationService().verify(cluster)
        for cluster in NewsClusterer().cluster(filter_result.candidates)
    ]
    reports = {
        cluster.cluster_id: ClusterCredibilityService().evaluate(cluster)
        for cluster in clusters
    }
    return {
        "fetch_result": fetch_result,
        "dedup_result": dedup_result,
        "filter_result": filter_result,
        "clusters": clusters,
        "reports": reports,
    }


def _apply_lifecycle_updates(
    *,
    lifecycle_store: EventLifecycleStore,
    clusters,
    reports,
) -> tuple[list[Any], list[Any]]:
    matcher = EventLifecycleMatcher()
    updater = EventLifecycleUpdater()
    updates = []
    for cluster in clusters:
        report = reports[cluster.cluster_id]
        match = matcher.match(cluster, report, lifecycle_store.list_events())
        matched_event = lifecycle_store.get(match.tracked_event_id) if match.matched and match.tracked_event_id else None
        event, event_updates = updater.apply(cluster, report, matched_event=matched_event)
        lifecycle_store.upsert(event)
        updates.extend(event_updates)
    stale_updates = updater.mark_stale(lifecycle_store.list_events())
    return updates, stale_updates


def _started_record(config: SchedulerJobConfig) -> SchedulerRunRecord:
    return SchedulerRunRecord(
        job_id=config.job_id,
        job_type=config.job_type,
        started_at=utc_now(),
        status="started",
    )


def _scan_notes(config: SchedulerJobConfig) -> list[str]:
    notes = [
        f"source={config.source}",
        f"real_fetch={config.real_fetch}",
        f"dry_run={config.dry_run}",
    ]
    if not config.real_fetch:
        notes.append("Offline mock news registry used.")
    return notes
