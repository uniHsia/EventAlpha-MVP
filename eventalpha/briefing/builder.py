"""Deterministic builder for daily briefing reports."""

from __future__ import annotations

from collections import Counter
from typing import Any

from eventalpha.schemas.base import RISK_DISCLAIMER

from .schemas import BriefingCollectedData, BriefingItem, BriefingSection, DailyBriefing


class DailyBriefingBuilder:
    """Build a compact briefing from collected local state."""

    def __init__(self, *, max_items: int = 10) -> None:
        self.max_items = max(max_items, 1)

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
            warnings=_dedupe(collected_data.warnings),
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
        ]
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
        items = [
            BriefingItem(
                item_id=str(row.get("card_id")),
                title=str(row.get("event_title") or "Untitled event card"),
                item_type="event_card",
                priority=str(row.get("event_level") or "normal"),
                summary=row.get("one_sentence"),
                risk_notes=[str(item) for item in row.get("risk_factors", [])][:4],
                verification_indicators=[str(item) for item in row.get("verification_indicators", [])][:4],
                metadata={"event_id": row.get("event_id"), "credibility_score": row.get("credibility_score")},
            )
            for row in data.event_cards[: self.max_items]
        ]
        return BriefingSection(
            section_id="event_cards",
            title="事件卡片摘要",
            items=items,
            notes=[] if items else ["暂无持久化 EventCard。"],
        )

    def _history_validation_section(self, data: BriefingCollectedData) -> BriefingSection:
        history_cards = [row for row in data.event_cards if _contains_history_note(row)][: self.max_items]
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
                ],
                metadata={"prediction_id": row.get("prediction_id"), "event_id": row.get("event_id")},
            )
            for row in data.review_results[: self.max_items]
        ]
        return BriefingSection(section_id="auto_reviews", title="今日到期复盘", items=items, notes=_dedupe(notes))

    def _rule_updates_section(self, data: BriefingCollectedData) -> BriefingSection:
        items = [
            BriefingItem(
                item_id=str(row.get("update_id")),
                title=str(row.get("rule_id") or "rule_update"),
                item_type="rule_update",
                priority=str(row.get("update_action") or "unchanged"),
                summary=row.get("reason"),
                details=[
                    f"old_weight={row.get('old_weight')}",
                    f"new_weight={row.get('new_weight')}",
                    f"action={row.get('update_action')}",
                ],
                metadata={"prediction_id": row.get("prediction_id"), "summary_id": row.get("summary_id")},
            )
            for row in data.rule_updates[: self.max_items]
        ]
        return BriefingSection(
            section_id="rule_updates",
            title="规则更新",
            items=items,
            notes=[] if items else ["暂无 rule update。"],
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
        no_items = [warning for warning in data.warnings if "no items" in warning.casefold()][:3]
        notes = [
            f"Configured scheduler jobs: {len(data.scheduler_jobs)}.",
            f"Recent runs: {len(data.recent_runs)}.",
            f"Run statuses: {dict(status_counts)}.",
            f"Recent job types: {dict(job_counts)}.",
        ]
        notes.extend(f"Recent no-items warning: {warning}" for warning in no_items)
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
                risk_notes=run.warnings[:2] + run.errors[:2],
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
