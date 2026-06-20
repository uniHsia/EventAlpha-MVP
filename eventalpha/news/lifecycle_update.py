"""Lifecycle update logic for tracked events."""

from __future__ import annotations

from datetime import datetime, timedelta

from eventalpha.schemas.base import utc_now

from .lifecycle import (
    EventLifecycleUpdate,
    EventTimelineEntry,
    TrackedEvent,
    stage_from_credibility,
    tracked_event_from_cluster,
)
from .schemas import ClusterCredibilityReport, EventCluster


UPGRADE_STATUSES = {"multi_source_supported", "high_confidence"}
LOW_STATUSES = {"single_source_low_confidence", "unconfirmed_or_considering", None}


class EventLifecycleUpdater:
    """Apply cluster and credibility updates to tracked events."""

    def apply(
        self,
        cluster: EventCluster,
        credibility_report: ClusterCredibilityReport,
        matched_event: TrackedEvent | None = None,
        now: datetime | None = None,
    ) -> tuple[TrackedEvent, list[EventLifecycleUpdate]]:
        """Create or update lifecycle state for a cluster."""
        timestamp = now or utc_now()
        if matched_event is None:
            event = tracked_event_from_cluster(cluster, credibility_report, now=timestamp)
            update = EventLifecycleUpdate(
                tracked_event_id=event.tracked_event_id,
                update_type="new_event",
                old_stage=None,
                new_stage=event.lifecycle_stage,
                cluster_id=cluster.cluster_id,
                changed_fields=["tracked_event_id", "lifecycle_stage", "cluster_ids"],
                notes=[f"Created tracked event from cluster {cluster.cluster_id}."],
            )
            return event, [update]

        event = matched_event.model_copy(deep=True)
        old_stage = event.lifecycle_stage
        old_source_count = event.source_count
        old_credibility = event.credibility_status
        old_official = event.official_evidence_status
        updates: list[EventLifecycleUpdate] = [
            EventLifecycleUpdate(
                tracked_event_id=event.tracked_event_id,
                update_type="matched_existing",
                old_stage=old_stage,
                new_stage=old_stage,
                cluster_id=cluster.cluster_id,
                changed_fields=[],
                notes=[f"Cluster {cluster.cluster_id} matched existing event."],
            )
        ]

        changed_fields = self._merge_event(event, cluster, credibility_report, timestamp)
        new_stage = _resolve_stage(old_stage, credibility_report.credibility_status)
        event.lifecycle_stage = new_stage
        event.is_active = new_stage not in {"closed", "resolved"}

        if event.source_count > old_source_count:
            updates.append(_update(event, "source_count_increased", old_stage, new_stage, cluster, ["source_count"]))
        if old_credibility in LOW_STATUSES and credibility_report.credibility_status in UPGRADE_STATUSES:
            updates.append(_update(event, "credibility_upgraded", old_stage, new_stage, cluster, ["credibility_status"]))
        if old_official != "official_source_present" and credibility_report.official_evidence_status == "official_source_present":
            updates.append(
                _update(event, "official_evidence_added", old_stage, new_stage, cluster, ["official_evidence_status"])
            )
        if credibility_report.credibility_status == "conflicting_claims":
            updates.append(_update(event, "conflict_detected", old_stage, new_stage, cluster, ["lifecycle_stage"]))
        if credibility_report.credibility_status == "unconfirmed_or_considering":
            updates.append(_update(event, "uncertainty_detected", old_stage, new_stage, cluster, ["lifecycle_stage"]))
        if credibility_report.credibility_status == "analysis_only":
            updates.append(_update(event, "analysis_only_detected", old_stage, new_stage, cluster, ["lifecycle_stage"]))

        if changed_fields or old_stage != new_stage:
            event.timeline.append(
                EventTimelineEntry(
                    timestamp=timestamp,
                    update_type="matched_existing",
                    cluster_id=cluster.cluster_id,
                    title=cluster.canonical_title,
                    summary=cluster.canonical_summary,
                    source_count=event.source_count,
                    credibility_status=credibility_report.credibility_status,
                    official_evidence_status=credibility_report.official_evidence_status,
                    notes=[f"Updated fields: {', '.join(changed_fields) or 'stage only'}."],
                )
            )
        for update in updates:
            update.new_stage = new_stage
        return event, updates

    def mark_stale(
        self,
        events: list[TrackedEvent],
        now: datetime | None = None,
        stale_after_days: int = 7,
        close_after_days: int = 30,
    ) -> list[EventLifecycleUpdate]:
        """Mark old active events as stale or closed."""
        timestamp = now or utc_now()
        updates: list[EventLifecycleUpdate] = []
        for event in events:
            if not event.is_active:
                continue
            age = timestamp - event.last_seen_at
            if event.lifecycle_stage == "stale" and age > timedelta(days=close_after_days):
                old_stage = event.lifecycle_stage
                event.lifecycle_stage = "closed"
                event.is_active = False
                updates.append(_stale_update(event, "event_closed", old_stage, timestamp))
            elif event.lifecycle_stage != "stale" and age > timedelta(days=stale_after_days):
                old_stage = event.lifecycle_stage
                event.lifecycle_stage = "stale"
                updates.append(_stale_update(event, "event_stale", old_stage, timestamp))
        return updates

    def _merge_event(
        self,
        event: TrackedEvent,
        cluster: EventCluster,
        credibility_report: ClusterCredibilityReport,
        timestamp: datetime,
    ) -> list[str]:
        changed: list[str] = []
        if cluster.cluster_id not in event.cluster_ids:
            event.cluster_ids.append(cluster.cluster_id)
            changed.append("cluster_ids")
        for source in cluster.sources:
            if source not in event.sources:
                event.sources.append(source)
                changed.append("sources")
        if len(event.sources) > event.source_count:
            event.source_count = len(event.sources)
            changed.append("source_count")
        if timestamp > event.last_seen_at:
            event.last_seen_at = timestamp
            changed.append("last_seen_at")
        if cluster.canonical_summary and cluster.canonical_summary != event.current_summary:
            event.current_summary = cluster.canonical_summary
            changed.append("current_summary")
        if credibility_report.credibility_status != event.credibility_status:
            event.credibility_status = credibility_report.credibility_status
            changed.append("credibility_status")
        if credibility_report.official_evidence_status != event.official_evidence_status:
            event.official_evidence_status = credibility_report.official_evidence_status
            changed.append("official_evidence_status")
        for claim in credibility_report.claims:
            if claim.claim_text not in event.latest_claims:
                event.latest_claims.append(claim.claim_text)
                changed.append("latest_claims")
        for keyword in cluster.dominant_keywords:
            if keyword not in event.dominant_keywords:
                event.dominant_keywords.append(keyword)
                changed.append("dominant_keywords")
        return _unique(changed)


def _resolve_stage(old_stage: str, credibility_status: str | None) -> str:
    candidate = stage_from_credibility(credibility_status)
    if old_stage in {"closed", "resolved"}:
        return old_stage
    if candidate == "conflicting":
        return "conflicting"
    if old_stage == "conflicting" and candidate != "confirmed":
        return "conflicting"
    if candidate == "analysis_only":
        return "analysis_only"
    if candidate == "confirmed":
        return "confirmed"
    if candidate == "unconfirmed_or_considering":
        return "unconfirmed_or_considering"
    if old_stage == "new":
        return "developing"
    if old_stage == "stale":
        return "developing"
    return old_stage


def _update(
    event: TrackedEvent,
    update_type: str,
    old_stage: str | None,
    new_stage: str | None,
    cluster: EventCluster,
    changed_fields: list[str],
) -> EventLifecycleUpdate:
    return EventLifecycleUpdate(
        tracked_event_id=event.tracked_event_id,
        update_type=update_type,
        old_stage=old_stage,
        new_stage=new_stage,
        cluster_id=cluster.cluster_id,
        changed_fields=changed_fields,
        notes=[f"{update_type} detected for cluster {cluster.cluster_id}."],
    )


def _stale_update(
    event: TrackedEvent,
    update_type: str,
    old_stage: str,
    timestamp: datetime,
) -> EventLifecycleUpdate:
    event.timeline.append(
        EventTimelineEntry(
            timestamp=timestamp,
            update_type=update_type,
            title=event.canonical_title,
            source_count=event.source_count,
            credibility_status=event.credibility_status,
            official_evidence_status=event.official_evidence_status,
            notes=[f"Lifecycle stage changed from {old_stage} to {event.lifecycle_stage}."],
        )
    )
    return EventLifecycleUpdate(
        tracked_event_id=event.tracked_event_id,
        update_type=update_type,
        old_stage=old_stage,
        new_stage=event.lifecycle_stage,
        changed_fields=["lifecycle_stage", "is_active"],
        notes=[f"Event marked {event.lifecycle_stage} due to inactivity."],
    )


def _unique(values) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
