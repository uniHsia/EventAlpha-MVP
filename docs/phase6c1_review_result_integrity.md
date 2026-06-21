# Phase 6C.1 Auto Review Result Integrity

Phase 6C.1 fixes the integrity boundary for automatic reviews. A due task is not considered reviewed unless it produces at least one asset-level `ReviewResult`.

## Why assets=0 and results=0 Was a Problem

Prediction assets are stored on the `PredictionLedgerEntry`, while review tasks represent matured review windows such as `T+1`, `T+3`, and `T+7`. The original auto-review path counted only assets whose original `time_window` matched the task horizon. Demo predictions often store all assets as `T+3`, so a due `T+1` task could show `assets=0`, produce `results=0`, still save an empty summary/rule update, and mark the task completed.

## Asset Count

`ReviewDueTaskView.asset_count` now counts all `prediction.predicted_assets` for the linked prediction. The task horizon is the review window, not an asset inclusion filter.

## Reviewed vs Skipped

`AutoReviewRunner` counts a task as reviewed only when the review pipeline returns one or more `ReviewResult` rows. On success the task note includes:

```text
Reviewed task: ... assets=5 results=5 rule_updates=1
```

If a prediction has no assets, the task is skipped:

```text
Skipped task: ... assets=0 reason=no_predicted_assets
```

If a pipeline returns zero review results, the task is skipped:

```text
Skipped task: ... reason=no_review_results
```

Skipped tasks are not marked completed.

## Rule Updates

Rule updates are counted and saved only when at least one `ReviewResult` exists. Empty result sets do not generate rule updates.

## Demo Fixture

Use `--demo-create-due-review` to create an isolated demo ledger under `data/cache/auto_review_demo.sqlite3` unless `--ledger-path` is provided:

```bash
python scripts/run_scheduler.py --once review_due_scan --demo-create-due-review
python scripts/run_scheduler.py --once auto_review_runner --execute --market-provider mock --demo-create-due-review
```

The fixture creates an AI export-control prediction with five predicted assets and one due `T+1` task. It does not write the default SQLite ledger.

## Boundaries

This phase still does not add UI, daily briefing, push delivery, LLM calls, real event studies, automatic trading, buy/sell/target-price output, ledger schema changes, or repository schema changes. It reuses existing horizon return logic and records results for event research and market analysis only, not investment advice.
