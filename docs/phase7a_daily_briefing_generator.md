# Phase 7A Daily Briefing Generator

Phase 7A adds an offline report layer after scheduler priority tracking and auto-review automation. It summarizes local EventAlpha state into Markdown and JSON artifacts for event research and market analysis.

## Schemas

`BriefingItem` is the smallest report row. It stores title, item type, priority, summary text, details, risk notes, verification indicators, source refs, and metadata.

`BriefingSection` groups items under a stable section id and display title.

`DailyBriefing` stores the report id, briefing date, generation timestamp, title, sections, warnings, and the required non-investment disclaimer.

## Data Collector

`BriefingDataCollector` reads local state only:

- active lifecycle events from `EventLifecycleStore`
- scheduler config, recent run logs, and tracking policies from `SchedulerStateStore`
- current urgency scores from `EventPriorityRanker`
- latest EventCards, ReviewResults, review summaries, and RuleUpdates from SQLite when the ledger file already exists

The collector does not fetch news, call LLMs, call market providers, run review jobs, or write the ledger. Missing files produce notes instead of failures.

## Builder

`DailyBriefingBuilder` creates these sections:

- `new_events`
- `urgent_events`
- `lifecycle_updates`
- `event_cards`
- `history_validation`
- `auto_reviews`
- `rule_updates`
- `tomorrow_watchlist`
- `system_status`

Urgent and high priority events are shown first. Background and analysis-only events are excluded from the main focus sections. Auto-review sections show reviewed tasks, ReviewResult counts, RuleUpdate counts, skipped or failed task notes, and recent review rows when available.

History validation signals are displayed only as local explanatory signals. Demo-only or mock data must remain marked as illustrative and cannot be treated as real market evidence.

## Rendering And Reports

`MarkdownBriefingRenderer` produces a compact Markdown report with Chinese section headings and the required risk disclaimer.

`JSONBriefingWriter` writes:

```text
reports/daily_briefing_YYYYMMDD.md
reports/daily_briefing_YYYYMMDD.json
```

The CLI prints Markdown by default. It writes report files only with `--write-report`.

```bash
python scripts/run_daily_briefing.py
python scripts/run_daily_briefing.py --write-report
python scripts/run_daily_briefing.py --date 2026-06-21
python scripts/run_daily_briefing.py --max-items 10
```

## Scheduler Job

The optional `daily_briefing` scheduler job is registered with the same dry-run/execute pattern as other scheduler jobs.

```bash
python scripts/run_scheduler.py --once daily_briefing
python scripts/run_scheduler.py --once daily_briefing --execute
```

Dry-run builds the briefing and records scheduler notes but does not write reports. Execute writes local Markdown and JSON reports. The job never fetches news, runs review, writes ledger rows, or calls LLMs.

## Boundaries

Phase 7A does not add Streamlit UI, WeChat push, email push, daily deployment, automatic trading, buy/sell instructions, target prices, LLM generation, real market fetching, ledger schema changes, or repository schema changes.

Phase 7A.1 adds presentation deduplication for repeated EventCards, ReviewResults, RuleUpdates, and warnings. See `docs/phase7a1_briefing_dedup_polish.md`.

This content is for event research and market analysis only. It is not investment advice.
