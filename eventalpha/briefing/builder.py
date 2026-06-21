"""Deterministic builder for polished daily briefing reports."""

from __future__ import annotations

from collections import Counter
from typing import Any

from eventalpha.schemas.base import RISK_DISCLAIMER

from .presentation import (
    aggregate_messages,
    extract_prediction_ids_from_notes,
    is_background_analysis_event,
    latest_sort_key,
    normalize_text,
)
from .schemas import BriefingCollectedData, BriefingItem, BriefingSection, DailyBriefing


class DailyBriefingBuilder:
    """Build a compact briefing from collected local state."""

    def __init__(self, *, max_items: int = 10) -> None:
        self.max_items = max(max_items, 1)
        self.compact_limit = min(self.max_items, 5)

    def build(self, collected_data: BriefingCollectedData) -> DailyBriefing:
        """Assemble all briefing sections."""
        sections = [
            self._new_events_section(collected_data),
            self._urgent_events_section(collected_data),
            self._lifecycle_updates_section(collected_data),
            self._event_cards_section(collected_data),
            self._history_validation_section(collected_data),
            self._auto_reviews_section(collected_data),
            self._rule_updates_section(collected_data),
            self._tomorrow_watchlist_section(collected_data),
            self._system_status_section(collected_data),
        ]
        return DailyBriefing(
            briefing_date=collected_data.briefing_date,
            title=f"EventAlpha Daily Briefing - {collected_data.briefing_date.isoformat()}",
            sections=sections,
            warnings=aggregate_messages(collected_data.warnings, limit=3),
            risk_disclaimer=RISK_DISCLAIMER,
        )

    def _new_events_section(self, data: BriefingCollectedData) -> BriefingSection:
        scores_by_id = {score.tracked_event_id: score for score in data.urgency_scores}
        events = [
            event
            for event in data.active_events
            if event.lifecycle_stage in {"new", "developing", "confirmed"}
            and event.tracked_event_id in scores_by_id
            and scores_by_id[event.tracked_event_id].urgency_level not in {"background", "ignore"}
            and not is_background_analysis_event(event)
        ]
        events.sort(
            key=lambda event: (
                {"urgent": 0, "high": 1, "normal": 2}.get(
                    scores_by_id[event.tracked_event_id].urgency_level, 3
                ),
                -scores_by_id[event.tracked_event_id].urgency_score,
            )
        )
        items = [
            BriefingItem(
                item_id=event.tracked_event_id,
                title=event.canonical_title,
                item_type="lifecycle_event",
                priority=scores_by_id[event.tracked_event_id].urgency_level,
                summary=event.current_summary,
                details=[
                    f"stage={event.lifecycle_stage}",
                    f"sources={event.source_count}",
                    f"credibility={event.credibility_status or 'unknown'}",
                ],
                source_refs=event.sources[:3],
                metadata={"tracked_event_id": event.tracked_event_id},
            )
            for event in events[: self.max_items]
        ]
        return BriefingSection(
            section_id="new_events",
            title="今日重点事件",
            items=items,
            notes=[] if items else ["暂无重点新事件。"],
        )

    def _urgent_events_section(self, data: BriefingCollectedData) -> BriefingSection:
        scores = [
            score
            for score in data.urgency_scores
            if score.urgency_level in {"urgent", "high"}
        ][: self.max_items]
        items = [
            BriefingItem(
                item_id=score.tracked_event_id,
                title=score.title,
                item_type="urgency_score",
                priority=score.urgency_level,
                summary=f"urgency_score={score.urgency_score:.1f}",
                details=score.reasons[:4],
                risk_notes=score.penalties[:3],
                metadata={"urgency_score": score.urgency_score},
            )
            for score in scores
        ]
        return BriefingSection(
            section_id="urgent_events",
            title="高优先级 / 紧急跟踪",
            items=items,
            notes=[] if items else ["暂无 urgent/high 事件。"],
        )

    def _lifecycle_updates_section(self, data: BriefingCollectedData) -> BriefingSection:
        items: list[BriefingItem] = []
        for event in data.active_events[: self.max_items]:
            latest = event.timeline[-1] if event.timeline else None
            details = [
                f"last_seen={event.last_seen_at}",
                f"stage={event.lifecycle_stage}",
            ]
            if latest:
                details.append(f"latest_update={latest.update_type}")
                details.extend(latest.notes[:2])
            items.append(
                BriefingItem(
                    item_id=event.tracked_event_id,
                    title=event.canonical_title,
                    item_type="lifecycle_update",
                    priority=event.lifecycle_stage,
                    summary=event.current_summary,
                    details=details,
                    source_refs=event.sources[:3],
                )
            )
        return BriefingSection(
            section_id="lifecycle_updates",
            title="生命周期变化",
            items=items,
            notes=[] if items else ["暂无生命周期数据。"],
        )

    def _event_cards_section(self, data: BriefingCollectedData) -> BriefingSection:
        deduped_cards, duplicate_total = _dedupe_event_cards(data.event_cards)
        items = [
            BriefingItem(
                item_id=str(row.get("card_id")),
                title=str(row.get("event_title") or "Untitled event card"),
                item_type="event_card",
                priority=str(row.get("event_level") or "normal"),
                summary=row.get("one_sentence"),
                details=_duplicate_details(row),
                risk_notes=[str(item) for item in row.get("risk_factors", [])][:4],
                verification_indicators=[str(item) for item in row.get("verification_indicators", [])][:4],
                metadata={
                    "event_id": row.get("event_id"),
                    "event_type": row.get("event_type"),
                    "credibility_score": row.get("credibility_score"),
                    "duplicate_count": row.get("duplicate_count", 1),
                },
            )
            for row in deduped_cards[: self.compact_limit]
        ]
        notes = [] if items else ["暂无持久化 EventCard。"]
        if duplicate_total:
            notes.append(f"EventCard duplicates collapsed: {duplicate_total}.")
        if len(deduped_cards) > len(items):
            notes.append(f"还有 {len(deduped_cards) - len(items)} 条 EventCard 已省略。")
        return BriefingSection(
            section_id="event_cards",
            title="事件卡片摘要",
            items=items,
            notes=notes,
        )

    def _history_validation_section(self, data: BriefingCollectedData) -> BriefingSection:
        deduped_cards, _ = _dedupe_event_cards(data.event_cards)
        history_cards = [row for row in deduped_cards if _contains_history_note(row)][: self.compact_limit]
        items = [
            BriefingItem(
                item_id=str(row.get("card_id")),
                title=str(row.get("event_title") or "History validation"),
                item_type="history_validation",
                priority="demo_only" if _contains_demo_note(row) else "normal",
                summary="历史验证信号来自本地卡片风险/验证提示。",
                risk_notes=_history_risk_notes(row),
                verification_indicators=[str(item) for item in row.get("verification_indicators", [])][:4],
            )
            for row in history_cards
        ]
        return BriefingSection(
            section_id="history_validation",
            title="历史案例验证摘要",
            items=items,
            notes=[] if items else ["暂无持久化历史验证摘要；demo/mock 信号不会被视为真实市场证据。"],
        )

    def _auto_reviews_section(self, data: BriefingCollectedData) -> BriefingSection:
        review_runs = [run for run in data.recent_runs if run.job_type == "auto_review_runner"]
        latest = review_runs[0] if review_runs else None
        notes: list[str] = []
        if latest:
            notes.extend(
                [
                    f"Latest auto_review_runner status: {latest.status}.",
                    f"Due tasks: {latest.candidate_items}.",
                    f"Reviewed tasks: {latest.analyzed_events}.",
                ]
            )
            notes.extend(_review_count_notes(latest.notes))
        else:
            notes.append("No recent auto_review_runner run found.")
        if not data.review_results:
            notes.append("No recent review results.")

        preferred_prediction_ids = extract_prediction_ids_from_notes(latest.notes if latest else [])
        deduped_results, duplicate_total = _dedupe_review_results(
            data.review_results,
            preferred_prediction_ids=preferred_prediction_ids,
        )
        displayed_results = deduped_results[: self.compact_limit]
        if duplicate_total:
            notes.append(f"ReviewResult duplicates collapsed: {duplicate_total}.")
        omitted_count = max(len(deduped_results) - len(displayed_results), 0)
        if omitted_count:
            notes.append(f"还有 {omitted_count} 条已省略。")

        items = [
            BriefingItem(
                item_id=str(row.get("review_id")),
                title=f"{row.get('asset_name')} / {row.get('horizon')}",
                item_type="review_result",
                priority=str(row.get("causal_validity") or "unknown"),
                summary=row.get("review_conclusion"),
                details=[
                    f"direction_correct={bool(row.get('direction_correct'))}",
                    f"excess_return={row.get('excess_return')}",
                    f"error_type={row.get('error_type')}",
                ] + _duplicate_details(row),
                metadata={
                    "prediction_id": row.get("prediction_id"),
                    "event_id": row.get("event_id"),
                    "duplicate_count": row.get("duplicate_count", 1),
                },
            )
            for row in displayed_results
        ]
        return BriefingSection(section_id="auto_reviews", title="今日到期复盘", items=items, notes=_dedupe(notes))

    def _rule_updates_section(self, data: BriefingCollectedData) -> BriefingSection:
        grouped_updates = _aggregate_rule_updates(data.rule_updates)
        items = [
            BriefingItem(
                item_id=str(row.get("update_id")),
                title=_rule_update_title(row),
                item_type="rule_update",
                priority=str(row.get("update_action") or "unchanged"),
                summary=row.get("reason"),
                details=[
                    f"old_weight={row.get('old_weight')}",
                    f"new_weight={row.get('new_weight')}",
                    f"action={row.get('update_action')}",
                    f"count={row.get('count', 1)}",
                ],
                metadata={
                    "prediction_id": row.get("prediction_id"),
                    "summary_id": row.get("summary_id"),
                    "count": row.get("count", 1),
                },
            )
            for row in grouped_updates[: self.compact_limit]
        ]
        notes = [] if items else ["暂无 rule update。"]
        if len(grouped_updates) > len(items):
            notes.append(f"还有 {len(grouped_updates) - len(items)} 条 rule update 分组已省略。")
        return BriefingSection(
            section_id="rule_updates",
            title="规则更新",
            items=items,
            notes=notes,
        )

    def _tomorrow_watchlist_section(self, data: BriefingCollectedData) -> BriefingSection:
        policies_by_id = {policy.tracked_event_id: policy for policy in data.tracking_policies}
        items = []
        for score in data.urgency_scores:
            policy = policies_by_id.get(score.tracked_event_id)
            if score.urgency_level in {"background", "ignore"}:
                continue
            items.append(
                BriefingItem(
                    item_id=score.tracked_event_id,
                    title=score.title,
                    item_type="watchlist",
                    priority=score.urgency_level,
                    summary=policy.reason if policy else "Watch for lifecycle and credibility changes.",
                    details=[
                        f"tracking_mode={policy.tracking_mode if policy else 'unsaved'}",
                        f"scan_interval_minutes={policy.scan_interval_minutes if policy else 'n/a'}",
                    ],
                    verification_indicators=score.reasons[:3],
                )
            )
            if len(items) >= self.max_items:
                break
        return BriefingSection(
            section_id="tomorrow_watchlist",
            title="明日关注指标",
            items=items,
            notes=[] if items else ["暂无明日重点 watchlist。"],
        )

    def _system_status_section(self, data: BriefingCollectedData) -> BriefingSection:
        status_counts = Counter(run.status for run in data.recent_runs)
        job_counts = Counter(run.job_type for run in data.recent_runs)
        warning_summaries = aggregate_messages(data.warnings, limit=3)
        notes = [
            f"Configured scheduler jobs: {len(data.scheduler_jobs)}.",
            f"Recent runs: {len(data.recent_runs)}.",
            f"Run statuses: {dict(status_counts)}.",
            f"Recent job types: {dict(job_counts)}.",
        ]
        notes.extend(f"Recent warning: {warning}" for warning in warning_summaries)
        notes.extend(data.notes[:5])
        items = [
            BriefingItem(
                item_id=run.run_id,
                title=run.job_type,
                item_type="scheduler_run",
                priority=run.status,
                summary=f"status={run.status}",
                details=[
                    f"started_at={run.started_at}",
                    f"candidate_items={run.candidate_items}",
                    f"analyzed_events={run.analyzed_events}",
                ],
                risk_notes=aggregate_messages(run.errors, limit=2),
            )
            for run in data.recent_runs[: self.max_items]
        ]
        return BriefingSection(
            section_id="system_status",
            title="系统状态与风险提示",
            items=items,
            notes=_dedupe(notes),
        )


def _contains_history_note(row: dict[str, Any]) -> bool:
    text = " ".join(str(item) for item in row.get("risk_factors", []) + row.get("verification_indicators", []))
    lowered = text.casefold()
    return any(term in lowered for term in ["history", "historical", "demo", "case-based", "历史"])


def _contains_demo_note(row: dict[str, Any]) -> bool:
    text = " ".join(str(item) for item in row.get("risk_factors", []) + row.get("verification_indicators", []))
    return "demo" in text.casefold() or "演示" in text


def _history_risk_notes(row: dict[str, Any]) -> list[str]:
    notes = [str(item) for item in row.get("risk_factors", [])][:4]
    if _contains_demo_note(row) and not any("demo" in note.casefold() or "演示" in note for note in notes):
        notes.append("历史信号为演示性质，不是真实市场证据。")
    return notes


def _review_count_notes(notes: list[str]) -> list[str]:
    return [
        note
        for note in notes
        if "ReviewResult count" in note or "RuleUpdate count" in note or "Reviewed task" in note
    ][:6]


def _dedupe_event_cards(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    event_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        event_id = str(row.get("event_id") or "").strip()
        if event_id:
            key = f"event_id::{event_id}"
        else:
            key = "::".join(
                [
                    "no_event_id",
                    normalize_text(row.get("event_title")),
                    normalize_text(row.get("event_type")),
                    normalize_text(row.get("one_sentence")),
                ]
            )
        event_groups.setdefault(key, []).append(row)

    representatives: list[dict[str, Any]] = []
    for grouped in event_groups.values():
        latest = max(grouped, key=latest_sort_key).copy()
        latest["duplicate_count"] = len(grouped)
        representatives.append(latest)

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in representatives:
        title_key = normalize_text(row.get("event_title"))
        event_type_key = normalize_text(row.get("event_type"))
        content_key = "::".join(
            [
                title_key,
                event_type_key,
                normalize_text(row.get("one_sentence")),
            ]
        )
        if title_key and event_type_key:
            key = f"title_type::{title_key}::{event_type_key}"
        elif title_key:
            key = f"title::{title_key}"
        elif event_id:
            key = f"event_id::{event_id}"
        else:
            key = f"content::{content_key}"
        groups.setdefault(key, []).append(row)

    deduped: list[dict[str, Any]] = []
    duplicate_total = 0
    for grouped in groups.values():
        latest = max(grouped, key=latest_sort_key).copy()
        duplicate_count = sum(int(row.get("duplicate_count") or 1) for row in grouped)
        latest["duplicate_count"] = duplicate_count
        duplicate_total += max(duplicate_count - 1, 0)
        deduped.append(latest)
    deduped.sort(key=latest_sort_key, reverse=True)
    return deduped, duplicate_total


def _dedupe_review_results(
    rows: list[dict[str, Any]],
    *,
    preferred_prediction_ids: list[str],
) -> tuple[list[dict[str, Any]], int]:
    preferred = set(preferred_prediction_ids)
    ordered_rows = sorted(
        rows,
        key=lambda row: (
            1 if row.get("prediction_id") in preferred else 0,
            *latest_sort_key(row),
        ),
        reverse=True,
    )
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in ordered_rows:
        key = "::".join(
            [
                str(row.get("prediction_id") or ""),
                normalize_text(row.get("asset_name")),
                str(row.get("horizon") or ""),
            ]
        )
        groups.setdefault(key, []).append(row)

    deduped: list[dict[str, Any]] = []
    duplicate_total = 0
    for grouped in groups.values():
        latest = grouped[0].copy()
        latest["duplicate_count"] = len(grouped)
        duplicate_total += max(len(grouped) - 1, 0)
        deduped.append(latest)
    deduped.sort(
        key=lambda row: (
            1 if row.get("prediction_id") in preferred else 0,
            *latest_sort_key(row),
        ),
        reverse=True,
    )
    return deduped, duplicate_total


def _aggregate_rule_updates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = "::".join(
            [
                str(row.get("rule_id") or "rule_update"),
                str(row.get("update_action") or "unchanged"),
            ]
        )
        groups.setdefault(key, []).append(row)

    aggregated: list[dict[str, Any]] = []
    for grouped in groups.values():
        latest = max(grouped, key=latest_sort_key).copy()
        latest["count"] = len(grouped)
        aggregated.append(latest)
    aggregated.sort(key=latest_sort_key, reverse=True)
    return aggregated


def _rule_update_title(row: dict[str, Any]) -> str:
    rule_id = str(row.get("rule_id") or "rule_update")
    action = str(row.get("update_action") or "unchanged")
    count = int(row.get("count") or 1)
    return f"{rule_id} {action} ×{count}" if count > 1 else f"{rule_id} {action}"


def _duplicate_details(row: dict[str, Any]) -> list[str]:
    count = int(row.get("duplicate_count") or 1)
    return [f"duplicate_count={count}, showing latest only"] if count > 1 else []


def _dedupe(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results
