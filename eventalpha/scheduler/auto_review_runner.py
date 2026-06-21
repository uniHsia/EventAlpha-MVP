"""Automatic review runner for due Prediction Ledger review tasks."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from eventalpha.config import PROJECT_ROOT
from eventalpha.data_sources import (
    AkShareMarketDataProvider,
    CSVMarketDataProvider,
    MarketDataProvider,
    MockMarketDataProvider,
    ProviderRouter,
)
from eventalpha.agents import review_asset, summarize_reviews
from eventalpha.schemas import MarketDataError, PredictionLedgerEntry, ReviewTask
from eventalpha.services import LedgerService, update_rule_from_review

from .review_schemas import AutoReviewRunSummary, ReviewDueTaskView


ReviewPipelineRunner = Callable[..., dict[str, Any]]


class AutoReviewRunner:
    """Run due review tasks through the existing review pipeline."""

    def __init__(
        self,
        ledger_service: LedgerService | None = None,
        *,
        review_pipeline_runner: ReviewPipelineRunner | None = None,
    ) -> None:
        self.ledger_service = ledger_service or LedgerService()
        self.review_pipeline_runner = review_pipeline_runner or run_auto_review_pipeline

    def scan_due_tasks(
        self,
        *,
        limit: int = 5,
        horizons: list[str] | None = None,
    ) -> list[ReviewDueTaskView]:
        """Return compact views for due pending review tasks."""
        tasks = self.ledger_service.list_due_review_tasks(limit=limit, horizons=horizons)
        return [self._task_view(task) for task in tasks]

    def run(
        self,
        *,
        dry_run: bool = True,
        limit: int = 5,
        horizons: list[str] | None = None,
        market_provider: str = "mock",
        allow_partial_review: bool = True,
    ) -> AutoReviewRunSummary:
        """Run or preview automatic reviews for due tasks."""
        tasks = self.ledger_service.list_due_review_tasks(limit=limit, horizons=horizons)
        views = [self._task_view(task) for task in tasks]
        summary = AutoReviewRunSummary(
            due_task_count=len(tasks),
            due_tasks=views,
            notes=[f"Due review tasks: {len(tasks)}."],
        )
        if dry_run:
            return summary.model_copy(
                update={
                    "skipped_task_count": len(tasks),
                    "notes": summary.notes
                    + [f"Due task: {_view_note(view)}" for view in views]
                    + ["Dry-run: review pipeline and market provider were not called."],
                }
            )

        notes = list(summary.notes)
        warnings: list[str] = []
        errors: list[str] = []
        reviewed_task_count = 0
        skipped_task_count = 0
        failed_task_count = 0
        review_result_count = 0
        rule_update_count = 0

        for task in tasks:
            prediction = self.ledger_service.get_prediction(task.prediction_id)
            if prediction is None:
                warnings.append(f"Missing prediction for task {task.task_id}: {task.prediction_id}")
                skipped_task_count += 1
                continue
            asset_count = len(prediction.predicted_assets)
            if asset_count == 0:
                warning = f"Skipped task {task.task_id}: no_predicted_assets"
                warnings.append(warning)
                notes.append(f"Skipped task: {_task_note(task, prediction)} assets=0 reason=no_predicted_assets.")
                skipped_task_count += 1
                continue
            try:
                provider = build_market_provider(market_provider, prediction=prediction)
                result = self.review_pipeline_runner(
                    prediction=prediction,
                    ledger_service=self.ledger_service,
                    market_data=provider,
                    horizon=task.horizon,
                    persist=True,
                )
                review_results = list(result.get("review_results") or [])
                rule_update = result.get("rule_update")
                if not review_results:
                    warnings.append(f"Skipped task {task.task_id}: no_review_results")
                    notes.append(
                        f"Skipped task: {_task_note(task, prediction)} "
                        f"assets={asset_count} results=0 reason=no_review_results."
                    )
                    skipped_task_count += 1
                    continue
                reviewed_task_count += 1
                review_result_count += len(review_results)
                rule_update_count += 1 if rule_update is not None else 0
                self.ledger_service.update_review_task_status(task.task_id, "completed")
                notes.append(
                    f"Reviewed task: {_task_note(task, prediction)} "
                    f"assets={asset_count} results={len(review_results)} "
                    f"rule_updates={1 if rule_update is not None else 0}."
                )
            except (MarketDataError, RuntimeError, ValueError) as exc:
                message = f"Review failed for task {task.task_id}: {exc}"
                if allow_partial_review:
                    warnings.append(message)
                    skipped_task_count += 1
                    continue
                errors.append(message)
                failed_task_count += 1
            except Exception as exc:  # pragma: no cover - defensive per-task boundary
                errors.append(f"Unexpected review failure for task {task.task_id}: {exc}")
                failed_task_count += 1

        return AutoReviewRunSummary(
            due_task_count=len(tasks),
            reviewed_task_count=reviewed_task_count,
            skipped_task_count=skipped_task_count,
            failed_task_count=failed_task_count,
            review_result_count=review_result_count,
            rule_update_count=rule_update_count,
            errors=errors,
            warnings=warnings,
            notes=notes,
            due_tasks=views,
        )

    def _task_view(self, task: ReviewTask) -> ReviewDueTaskView:
        prediction = self.ledger_service.get_prediction(task.prediction_id)
        if prediction is None:
            return ReviewDueTaskView(
                task_id=task.task_id,
                prediction_id=task.prediction_id,
                event_id=task.event_id,
                horizon=task.horizon,
                due_at=task.due_at,
                status=task.status,
                notes=["Prediction not found."],
            )
        asset_count = len(prediction.predicted_assets)
        return ReviewDueTaskView(
            task_id=task.task_id,
            prediction_id=task.prediction_id,
            event_id=task.event_id,
            horizon=task.horizon,
            due_at=task.due_at,
            status=task.status,
            event_title=prediction.event_title,
            asset_count=asset_count,
        )


def build_market_provider(
    market_provider: str,
    *,
    prediction: PredictionLedgerEntry | None = None,
) -> MarketDataProvider:
    """Build a market provider for auto review execution."""
    provider = market_provider.casefold()
    if provider == "mock":
        return MockMarketDataProvider()
    if provider == "csv":
        return CSVMarketDataProvider(PROJECT_ROOT / "eventalpha/examples/market_prices_demo.csv")
    if provider == "router":
        return ProviderRouter(default_event_type=prediction.event_type if prediction else None)
    if provider == "akshare":
        return AkShareMarketDataProvider()
    raise ValueError(f"Unsupported market provider: {market_provider}")


def run_auto_review_pipeline(
    *,
    prediction: PredictionLedgerEntry,
    ledger_service: LedgerService,
    market_data: MarketDataProvider,
    horizon: str,
    persist: bool = True,
) -> dict[str, Any]:
    """Review all predicted assets for the due task horizon.

    The core review pipeline filters assets by their original time_window. Auto
    review tasks instead represent matured review windows, so every predicted
    asset should be reviewed against the due task horizon.
    """
    review_results = [
        review_asset(prediction, asset, market_data, horizon=horizon)
        for asset in prediction.predicted_assets
    ]
    if not review_results:
        return {
            "prediction": prediction,
            "review_result": None,
            "review_results": [],
            "review_summary": None,
            "rule_update": None,
        }
    review_summary = summarize_reviews(
        prediction.model_copy(
            update={
                "predicted_assets": [
                    asset.model_copy(update={"time_window": horizon})
                    for asset in prediction.predicted_assets
                ]
            }
        ),
        review_results,
        horizon=horizon,
    )
    rule_update = update_rule_from_review(prediction, review_summary)
    if persist:
        for review_result in review_results:
            ledger_service.save_review_result(review_result)
        ledger_service.save_review_summary(review_summary)
        ledger_service.save_rule_update(rule_update)
    return {
        "prediction": prediction,
        "review_result": review_results[0],
        "review_results": review_results,
        "review_summary": review_summary,
        "rule_update": rule_update,
    }


def _view_note(view: ReviewDueTaskView) -> str:
    return (
        f"{view.task_id} prediction={view.prediction_id} "
        f"title={view.event_title or 'unknown'} horizon={view.horizon} "
        f"due_at={view.due_at.isoformat()} assets={view.asset_count}"
    )


def _task_note(task: ReviewTask, prediction: PredictionLedgerEntry) -> str:
    return (
        f"{task.task_id} prediction={task.prediction_id} "
        f"title={prediction.event_title} horizon={task.horizon}"
    )
