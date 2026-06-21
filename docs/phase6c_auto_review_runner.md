# Phase 6C Auto Review Runner

Phase 6C adds scheduler jobs for automatic review of due Prediction Ledger review tasks. It builds on Phase 6B priority scheduling by closing the loop for matured `T+1`, `T+3`, and `T+7` review windows.

Defaults remain safe: dry-run, mock market provider, no LLM, no network, no UI or push, no trading output, and no ledger schema changes.

## ReviewDueTaskView

`ReviewDueTaskView` is a compact scheduler display model for due tasks. It includes task id, prediction id, event id, horizon, due time, status, event title, matching asset count, and notes. It does not replace or modify the core `ReviewTask` schema.

## AutoReviewRunSummary

`AutoReviewRunSummary` records auto-review counters:

- due tasks
- reviewed tasks
- skipped tasks
- failed tasks
- review result count
- rule update count
- errors, warnings, notes

The summary is folded into `SchedulerRunRecord` notes, warnings, errors, `candidate_items`, and `analyzed_events`.

## review_due_scan

`review_due_scan` reads pending review tasks whose `due_at <= now`. It lists due tasks and never calls a market provider, never runs the review pipeline, and never writes ledger rows. It is safe as dry-run/status infrastructure.

```bash
python scripts/run_scheduler.py --once review_due_scan
```

## auto_review_runner

`auto_review_runner` first scans due tasks. In dry-run mode it lists the tasks that would be reviewed. In execute mode it calls the existing review pipeline for each due task, using the task horizon and selected market provider.

```bash
python scripts/run_scheduler.py --once auto_review_runner
python scripts/run_scheduler.py --once auto_review_runner --execute
python scripts/run_scheduler.py --once auto_review_runner --execute --market-provider csv
```

Successful execute runs may save `ReviewResult`, `PredictionReviewSummary`, `RuleUpdate`, and mark the reviewed task `completed`. This reuses existing ledger tables and services; no schema migration is introduced.

## Market Providers

Provider selection is explicit:

- `mock`: deterministic local mock provider and default
- `csv`: local demo CSV provider
- `router`: existing `ProviderRouter`
- `akshare`: explicit only; not used by tests

Pytest does not require network access.

## Partial Failure

Each due task is isolated. If one task fails because market data is missing or a provider route fails, the runner records a warning or error and continues to later tasks when `allow_partial_review=True`. Only successful tasks are marked completed.

## Boundaries

Phase 6C does not add a full event study. It reuses existing horizon return and review logic for `T+1`, `T+3`, and `T+7`. It does not call LLMs, change ledger schema, change repository schema, create UI, send notifications, produce daily briefings, do automatic trading, or output buy/sell/target-price instructions.

This content is for event research and market analysis only. It is not investment advice.
