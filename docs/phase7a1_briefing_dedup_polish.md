# Phase 7A.1 Daily Briefing Dedup And Presentation Polish

Phase 7A.1 cleans up the daily briefing output before it is used by a future Streamlit console. It does not add UI, push, LLM generation, network fetches, ledger writes, or ledger schema changes.

## Why This Phase Exists

Phase 7A proved the report pipeline worked, but local run logs and demo ledgers can contain repeated EventCards, repeated asset-level ReviewResults, repeated RuleUpdates, and repeated scheduler warnings. This phase keeps the underlying data intact and improves only the presentation layer.

## EventCard Dedup

EventCards are grouped by normalized `event_title + event_type` when both are available, so repeated runs of the same event collapse even if generated wording changes slightly. If title/type are missing, the grouping falls back to `event_id` and then normalized card content.

Only the latest row is shown. The briefing item metadata records `duplicate_count`, and Markdown can show `duplicate_count=N, showing latest only`.

## ReviewResult Dedup

`review_results` do not store `task_id`, so the briefing dedup key is:

```text
prediction_id + asset_name + horizon
```

Rows tied to the latest `auto_review_runner` prediction notes are prioritized. Within each group, the latest row is shown. The auto-review section shows run summary notes first, then up to five asset-level results, plus an omitted-count note when needed.

## RuleUpdate Aggregation

Rule updates are grouped by:

```text
rule_id + update_action
```

The latest weights and rationale are displayed with a count, for example:

```text
RULE_AI_EXPORT_001 slightly_strengthen ×10
```

## Background Filtering

`analysis_only` lifecycle events are excluded from today's focus events. Single-source think tank, commentary, foundation, Brookings, and Council on Foreign Relations style items are treated as background unless they have at least two sources and high or multi-source credibility.

Background items can still appear in lifecycle/system context, but they do not dominate the top-event section.

## Warning Aggregation

Repeated warnings are normalized and displayed as counted messages:

```text
RSS query matched no items. ×10
```

Top-level warnings and system-status notes show at most three warning types.

## Commands

Use the full Python command from the repository root:

```bash
python scripts/run_daily_briefing.py
python scripts/run_daily_briefing.py --write-report
```

Running only `run_daily_briefing.py --write-report` is not a supported command unless the script directory is already on your shell path.

## Boundary

The report remains an offline event research artifact and is not investment advice. It does not output buy/sell instructions or target prices.
