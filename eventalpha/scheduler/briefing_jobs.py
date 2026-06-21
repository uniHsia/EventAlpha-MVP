"""Scheduler integration for daily briefing generation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from eventalpha.news import DEFAULT_LIFECYCLE_STORE_PATH
from eventalpha.schemas.base import utc_now

from .schemas import SchedulerJobConfig, SchedulerRunRecord
from .state_store import DEFAULT_SCHEDULER_RUNS_PATH, DEFAULT_SCHEDULER_STATE_PATH, SchedulerStateStore


def run_daily_briefing_job(
    config: SchedulerJobConfig,
    store: SchedulerStateStore,
    *,
    briefing_date: date | None = None,
    reports_dir: str | Path = "reports",
    ledger_path: str | Path | None = None,
    lifecycle_store_path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH,
    state_path: str | Path = DEFAULT_SCHEDULER_STATE_PATH,
    runs_path: str | Path = DEFAULT_SCHEDULER_RUNS_PATH,
) -> SchedulerRunRecord:
    """Build a daily briefing and optionally write report files."""
    record = SchedulerRunRecord(
        job_id=config.job_id,
        job_type=config.job_type,
        started_at=utc_now(),
        status="started",
    )
    try:
        from eventalpha.briefing.builder import DailyBriefingBuilder
        from eventalpha.briefing.data_collector import BriefingDataCollector
        from eventalpha.briefing.json_writer import JSONBriefingWriter
        from eventalpha.briefing.markdown_renderer import MarkdownBriefingRenderer

        target_date = briefing_date or utc_now().date()
        collector = BriefingDataCollector(
            lifecycle_store_path=lifecycle_store_path,
            state_path=state_path,
            runs_path=runs_path,
            ledger_path=ledger_path,
            max_items=config.limit,
        )
        data = collector.collect(target_date)
        briefing = DailyBriefingBuilder(max_items=config.limit).build(data)
        markdown = MarkdownBriefingRenderer().render(briefing)
        notes = [
            f"Daily briefing generated for {target_date.isoformat()}.",
            f"Sections: {len(briefing.sections)}.",
            f"Markdown characters: {len(markdown)}.",
        ]
        if config.dry_run:
            notes.append("Dry-run: report files were not written.")
            status = "dry_run"
        else:
            paths = JSONBriefingWriter(reports_dir).write(briefing, markdown=markdown)
            notes.append(f"Markdown report: {paths['markdown']}.")
            notes.append(f"JSON report: {paths['json']}.")
            status = "success"
        record = record.model_copy(
            update={
                "candidate_items": len(data.active_events),
                "analyzed_events": len([section for section in briefing.sections if section.items]),
                "warnings": briefing.warnings,
                "notes": notes,
            }
        ).finish(status)
    except Exception as exc:  # pragma: no cover - defensive job boundary
        record = record.finish("failed", errors=record.errors + [str(exc)])
    store.append_run(record)
    return record
