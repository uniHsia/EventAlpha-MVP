# Phase 7B Streamlit Event Console

Phase 7B adds a read-only local console after the daily briefing polish work in
Phase 7A.1. The goal is to inspect the same local artifacts in a browser without
adding deployment, push, login, scheduler daemons, network fetches, LLM calls, or
ledger writes.

## Pages

- Dashboard: briefing summary, urgency counts, latest auto-review status,
  ReviewResult count, RuleUpdate count, recent warnings, and the risk disclaimer.
- Daily Briefing: latest local Markdown report, or an in-memory preview when no
  report file exists.
- Event Cards: deduped cards with level, title, summary, risk, verification, and
  duplicate count.
- Lifecycle: active tracked events split from analysis-only/background items.
- Reviews: deduped asset-level ReviewResults with return and causal-validity
  fields.
- Rule Updates: rule/action aggregation with count and latest weights.
- Scheduler Status: configured jobs, recent runs, tracking policies, warning
  aggregation, and local status notes.

## Data Sources

The console reads only local files:

- `reports/daily_briefing_*.md/json`
- `data/scheduler_state.json`
- `data/scheduler_runs.jsonl`
- `data/event_lifecycle_store.json`
- `eventalpha_mvp.sqlite3` in SQLite read-only mode

Missing files are shown as empty states. The loader does not initialize
`LedgerService`, create a new SQLite file, fetch news, call market providers, or
call LLMs.

## Run

Generate a local briefing first if you want the Daily Briefing page to show a
persisted report:

```bash
python scripts/run_daily_briefing.py --write-report
```

Start the console:

```bash
streamlit run app_streamlit.py
```

The console is local-only and does not start APScheduler daemon jobs. Scheduler
state is displayed from existing JSON state/run-log files.

## Boundary

This phase does not add login, deployment, WeChat/email push, daily automation,
automatic trading, buy/sell output, target prices, or schema migrations. Demo and
mock data must be treated as local research artifacts only.

本内容仅用于事件研究和市场分析，不构成投资建议。市场价格可能已提前反映相关信息，投资决策需结合个人风险承受能力。
