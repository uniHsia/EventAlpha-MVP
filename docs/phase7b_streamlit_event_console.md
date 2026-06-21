# Phase 7B Streamlit Event Console

Phase 7B adds a read-only local console after the daily briefing polish work in
Phase 7A.1. The goal is to inspect the same local artifacts in a browser without
adding deployment, push, login, scheduler daemons, network fetches, LLM calls, or
ledger writes.

## Pages

- Dashboard: Chinese teacher-friendly summary, urgency counts, Top Events,
  recent auto-review results, recent rule updates, friendly warnings, and the
  risk disclaimer.
- Daily Briefing: latest local Markdown report, or an in-memory preview when no
  report file exists.
- Event Cards: card-first view with level, title, summary, risk factors,
  verification indicators, duplicate count, and a folded raw table.
- Lifecycle: active tracked events split from analysis-only/background items,
  with Chinese stage and credibility explanations.
- Reviews: deduped asset-level ReviewResults with Chinese explanation,
  direction correctness, causal validity, error type, and return fields.
- Rule Updates: rule/action aggregation with count, latest weights, rationale,
  and Chinese action explanation.
- Scheduler Status: readable metrics, status/job-type tables, folded config,
  folded tracking policies, warning aggregation, and local status notes.

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

After running the Phase 7C full demo, start the same console in isolated demo
mode:

```bash
streamlit run app_streamlit.py -- --demo-mode
```

or:

```bash
EVENTALPHA_DEMO_MODE=1 streamlit run app_streamlit.py
```

Demo mode reads `data/demo/` and `reports/demo/` only. It remains read-only and
shows a prompt to run `python scripts/run_full_demo.py --reset-demo-state
--write-summary` when demo data is missing.

The console is local-only and does not start APScheduler daemon jobs. Scheduler
state is displayed from existing JSON state/run-log files.

Phase 7B.1 polishes the console for live demos. Warnings such as
`RSS query matched no items` are shown as friendly data-source notices on the
Dashboard, while raw warning text remains available inside expanders for
debugging. Raw JSON and wide tables are folded by default.

## Boundary

This phase does not add login, deployment, WeChat/email push, daily automation,
automatic trading, buy/sell output, target prices, or schema migrations. Demo and
mock data must be treated as local research artifacts only.

本内容仅用于事件研究和市场分析，不构成投资建议。市场价格可能已提前反映相关信息，投资决策需结合个人风险承受能力。
