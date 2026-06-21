"""Scheduler jobs for automatic Prediction Ledger reviews."""

from __future__ import annotations

from eventalpha.schemas.base import utc_now
from eventalpha.services import LedgerService

from .auto_review_runner import AutoReviewRunner, ReviewPipelineRunner, run_auto_review_pipeline
from .review_schemas import AutoReviewRunSummary
from .schemas import SchedulerJobConfig, SchedulerRunRecord
from .state_store import SchedulerStateStore


def run_review_due_scan(
    config: SchedulerJobConfig,
    store: SchedulerStateStore,
    *,
    ledger_service: LedgerService | None = None,
) -> SchedulerRunRecord:
    """Scan due review tasks without running market review."""
    record = _started_record(config)
    try:
        runner = AutoReviewRunner(ledger_service=ledger_service)
        views = runner.scan_due_tasks(
            limit=config.max_review_tasks,
            horizons=config.review_horizons,
        )
        notes = [f"Due review tasks: {len(views)}."]
        notes.extend(
            f"Due task: {view.task_id} prediction={view.prediction_id} "
            f"title={view.event_title or 'unknown'} horizon={view.horizon} "
            f"due_at={view.due_at.isoformat()} assets={view.asset_count}"
            for view in views
        )
        notes.append("Dry-run: review_due_scan does not call market providers or write ledger.")
        record = record.model_copy(
            update={
                "candidate_items": len(views),
                "notes": notes,
            }
        ).finish("success" if not config.dry_run else "dry_run")
    except Exception as exc:  # pragma: no cover - defensive job boundary
        record = record.finish("failed", errors=record.errors + [str(exc)])
    store.append_run(record)
    return record


def run_auto_review_runner(
    config: SchedulerJobConfig,
    store: SchedulerStateStore,
    *,
    ledger_service: LedgerService | None = None,
    review_pipeline_runner: ReviewPipelineRunner | None = None,
) -> SchedulerRunRecord:
    """Preview or execute due review tasks through the review pipeline."""
    record = _started_record(config)
    try:
        runner = AutoReviewRunner(
            ledger_service=ledger_service,
            review_pipeline_runner=review_pipeline_runner or run_auto_review_pipeline,
        )
        summary = runner.run(
            dry_run=config.dry_run,
            limit=config.max_review_tasks,
            horizons=config.review_horizons,
            market_provider=config.market_provider,
            allow_partial_review=config.allow_partial_review,
        )
        status = "dry_run" if config.dry_run else "success"
        if summary.errors and not summary.reviewed_task_count:
            status = "failed"
        record = _record_from_summary(record, summary).finish(status)
    except Exception as exc:  # pragma: no cover - defensive job boundary
        record = record.finish("failed", errors=record.errors + [str(exc)])
    store.append_run(record)
    return record


def _record_from_summary(
    record: SchedulerRunRecord,
    summary: AutoReviewRunSummary,
) -> SchedulerRunRecord:
    notes = list(summary.notes)
    notes.extend(
        [
            f"Reviewed tasks: {summary.reviewed_task_count}.",
            f"Skipped tasks: {summary.skipped_task_count}.",
            f"Failed tasks: {summary.failed_task_count}.",
            f"ReviewResult count: {summary.review_result_count}.",
            f"RuleUpdate count: {summary.rule_update_count}.",
        ]
    )
    return record.model_copy(
        update={
            "candidate_items": summary.due_task_count,
            "analyzed_events": summary.reviewed_task_count,
            "errors": list(summary.errors),
            "warnings": list(summary.warnings),
            "notes": notes,
        }
    )


def _started_record(config: SchedulerJobConfig) -> SchedulerRunRecord:
    return SchedulerRunRecord(
        job_id=config.job_id,
        job_type=config.job_type,
        started_at=utc_now(),
        status="started",
    )
