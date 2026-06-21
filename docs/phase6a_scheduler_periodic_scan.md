# Phase 6A Scheduler / Periodic Scan

Phase 6A adds a small scheduler layer after the EventCard and AntiSpurious history-validation integration. It packages existing news lifecycle scans and candidate event analysis into repeatable jobs while keeping the first version safe, local, and testable.

The scheduler is offline-first. It does not call LLMs by default, does not fetch real news unless `--real-fetch` is explicit, does not write Prediction Ledger rows unless `--persist` is explicit for candidate analysis, and does not change ledger schema.

## Schemas

`SchedulerJobConfig` defines one job:

- `job_type`: `news_lifecycle_scan`, `candidate_analysis`, or `scheduler_status`
- `interval_minutes`
- `query`, `source`, `rss_feed`, `limit`
- safety flags: `real_fetch`, `use_llm_extraction`, `use_llm_causal`, `use_llm_anti_spurious`, `persist`, `dry_run`

Defaults are conservative: `dry_run=True`, `real_fetch=False`, `persist=False`, and all LLM flags false.

`SchedulerRunRecord` stores one run:

- run identity and timestamps
- status: `started`, `success`, `failed`, `skipped`, or `dry_run`
- counters for fetched items, candidate items, clusters, lifecycle updates, and analyzed events
- errors and notes

## State Store

`SchedulerStateStore` uses readable local files:

- `data/scheduler_state.json`
- `data/scheduler_runs.jsonl`

It can save/load job config, append run records, list recent runs, and return the last successful run per job. Tests use temporary paths.

## Jobs

`news_lifecycle_scan` runs the Phase 4 news flow: fetch, deduplicate, keyword-filter, cluster, credibility, and lifecycle update. Dry-run performs the work in memory and does not save the lifecycle store. Execute mode can update only the lifecycle JSON store. It never writes the Prediction Ledger.

`candidate_analysis` reads active events from the lifecycle store. Dry-run lists the events that would be analyzed and does not call the event pipeline. Execute mode converts active lifecycle events to `RawNews` and runs the existing event pipeline with `persist=False` by default.

LLM extraction, causal reasoning, and anti-spurious agents are disabled by default. CLI LLM flags are explicit opt-ins for candidate analysis and are not used by tests.

`scheduler_status` reads scheduler config, recent runs, active event count, last successful runs, and recent errors. It does not fetch news, call LLMs, run pipeline analysis, or write ledger rows.

## CLI

Dry-run once:

```bash
python scripts/run_scheduler.py --once scheduler_status
python scripts/run_scheduler.py --once news_lifecycle_scan
python scripts/run_scheduler.py --once candidate_analysis
```

Execute local mock scan:

```bash
python scripts/run_scheduler.py --once news_lifecycle_scan --execute
```

Real RSS manual scan:

```bash
python scripts/run_scheduler.py --once news_lifecycle_scan --execute --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10
```

Daemon infrastructure:

```bash
python scripts/run_scheduler.py --daemon --interval-minutes 60
```

The daemon uses APScheduler with in-memory interval jobs only. Phase 6A does not add a persistent job store or deployment service.

## Safety Boundary

`--dry-run` means no lifecycle store mutation for scans, no event pipeline call for candidate analysis, no ledger writes, and no network.

`--execute` allows the job action to run. For `news_lifecycle_scan`, execute may update the lifecycle JSON store. For `candidate_analysis`, execute runs the pipeline but still uses `persist=False` unless `--persist` is explicitly provided.

`--real-fetch` is required for network news providers. Pytest never uses real network.

## Risk Notice

Scheduler output is for event research and market analysis only. It does not provide investment advice, trading instructions, target prices, or buy/sell recommendations.
