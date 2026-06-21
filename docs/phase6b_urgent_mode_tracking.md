# Phase 6B Urgent Mode / High-Frequency Tracking

Phase 6B adds a deterministic priority layer on top of the Phase 6A scheduler. It classifies active lifecycle events into urgent, high, normal, background, or ignore, then builds tracking policies and uses those priorities to choose candidate analysis inputs.

The phase remains offline-first and safe by default: dry-run is enabled, real fetch is disabled, LLM flags are disabled, ledger persistence is disabled, and no ledger schema changes are introduced.

## Why Urgent Mode Follows Phase 6A

Phase 6A made lifecycle scans and candidate analysis runnable as scheduler jobs. Phase 6B decides which active lifecycle events deserve attention first. This keeps high-impact, credible, recently updated events ahead of analysis-only commentary or stale low-confidence items.

## EventUrgencyScore

`EventUrgencyScore` records one lifecycle event's priority:

- `tracked_event_id`
- `title`
- `urgency_score`, clamped to `0..100`
- `urgency_level`: `urgent`, `high`, `normal`, `background`, or `ignore`
- `reasons`
- `penalties`

Score thresholds are:

- `urgent`: `>=75`
- `high`: `55..74`
- `normal`: `30..54`
- `background`: `10..29`
- `ignore`: `<10` or inactive/closed

Hard caps keep unsafe escalation conservative:

- `analysis_only` is capped at `background`
- `unconfirmed_or_considering` is capped at `high`
- `stale` is capped at `background`
- closed, resolved, or inactive events become `ignore`

## Priority Ranking Rules

`EventPriorityRanker` uses lifecycle fields only. It does not fetch news, call LLMs, run market data, or write ledger rows.

Positive weights include:

- new or developing lifecycle stage
- high-confidence or multi-source credibility
- official-source evidence
- source count of at least two or four
- high-impact terms such as conflict, war, attack, rate, tariff, export control, AI chip, earthquake, or geopolitical
- metadata or timeline notes containing `event_level=A` or `trigger_alert`
- historical validation terms such as `historically_weakened` or `requires_verification`
- update within the last 24 hours

Penalties include:

- analysis-only lifecycle stage
- single-source low confidence
- unconfirmed or considering
- stale lifecycle stage
- think tank, commentary, opinion, or research-only sources
- older than seven days

## TrackingPolicy

`TrackingPolicyService` turns urgency scores into per-event policies:

- urgent -> `tracking_mode=urgent`, `15` minutes, `analyze=True`
- high -> `tracking_mode=enhanced`, `30` minutes, `analyze=True`
- normal -> `tracking_mode=normal`, `60` minutes, `analyze=True`
- background -> `tracking_mode=background`, `240` minutes, `analyze=False`
- ignore -> `tracking_mode=paused`, `0` minutes, `analyze=False`

These intervals describe intended scheduler cadence. Tests never wait for real intervals.

## UrgentModeDecision

`UrgentModeDecision` is the compact urgent scan output. It contains urgent events, high-priority events, background events, tracking policies, and notes. Execute mode saves tracking policies into `data/scheduler_state.json` under `tracking_policies`; dry-run only appends the run log.

## Scheduler Jobs

`urgent_event_scan` reads active lifecycle events, ranks them, builds tracking policies, and records counts in the scheduler run log. It does not fetch news, call the event pipeline, call LLMs, write ledger rows, or mutate lifecycle state.

`candidate_analysis` now ranks active events before selection. It analyzes only top urgent, high, or normal events up to `limit` or `--top-n`. Background and ignored events are skipped by default. Dry-run prints what would be analyzed and why, and it does not call the pipeline.

`scheduler_status` now reports urgent, high, and background counts, top urgent titles, recent no-items warnings, recent runs, active event count, and last successful runs.

## No-Items Warnings

RSS messages like `RSS query matched no items.` are treated as warnings and notes, not hard errors. The scheduler run status remains success or dry-run when no-items warnings are the only issue. Real fetch failures, missing dependencies, and provider exceptions remain errors.

## Commands

Run urgent mode without mutating scheduler policy state:

```bash
python scripts/run_scheduler.py --once urgent_event_scan
```

Save tracking policies to scheduler state:

```bash
python scripts/run_scheduler.py --once urgent_event_scan --execute
```

Run priority-aware candidate analysis in dry-run:

```bash
python scripts/run_scheduler.py --once candidate_analysis --top-n 5
```

Show scheduler status:

```bash
python scripts/run_scheduler.py --once scheduler_status
```

Run a mock lifecycle scan that can update only the lifecycle JSON store:

```bash
python scripts/run_scheduler.py --once news_lifecycle_scan --execute
```

## Boundaries

Phase 6B does not add UI, push notifications, daily briefing, auto trading, buy/sell output, target prices, persistent APScheduler job stores, default real fetch, default LLM calls, default ledger writes, or ledger schema changes.

This content is for event research and market analysis only. It is not investment advice.
