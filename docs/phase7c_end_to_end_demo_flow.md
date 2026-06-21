# Phase 7C End-to-End Demo Flow

Phase 7C turns the Phase 7B.1 read-only console into a repeatable teacher-facing demo flow. Instead of relying on scattered local run history, `scripts/run_full_demo.py` creates an isolated offline scenario and runs the EventAlpha chain from event analysis through review, rule update, daily briefing, and Streamlit data validation.

## Scenario

The first supported scenario is `ai_export_control`.

- RawNews: 美国宣布升级 AI 芯片出口管制
- Source label: Reuters / Mock Global News
- Event type: `ai_export_control`
- Review horizon: `T+1`
- Demo assets: 国产 AI 芯片、服务器、先进封装、国产 EDA、半导体设备
- Market outcomes: deterministic mock/demo returns only

Reserved future scenario ids are `rate_policy`, `geopolitical_oil`, `trade_tariff`, and `earthquake_supply_chain`.

## Demo State Isolation

The default demo writes only to isolated paths:

```text
data/demo/eventalpha_demo.sqlite3
data/demo/scheduler_state.json
data/demo/scheduler_runs.jsonl
data/demo/event_lifecycle_store.json
reports/demo/
```

`--reset-demo-state` clears only `data/demo/` and `reports/demo/`. It does not remove the default `eventalpha_mvp.sqlite3`. `--use-default-state` is an explicit opt-in for local debugging and should not be used for repeatable demos.

## Usage

```bash
python scripts/run_full_demo.py --reset-demo-state --write-summary
python scripts/run_full_demo.py --scenario ai_export_control --write-summary
python scripts/run_full_demo.py --open-instructions
```

The script does not start Streamlit, does not start APScheduler daemon jobs, and does not open a browser. It prints the next command:

```bash
streamlit run app_streamlit.py -- --demo-mode
```

You can also use:

```bash
EVENTALPHA_DEMO_MODE=1 streamlit run app_streamlit.py
```

## Flow

1. Prepare isolated demo state.
2. Run the deterministic event-analysis pipeline into the demo Prediction Ledger.
3. Mark the T+1 review task as due.
4. Run `auto_review_runner` with the mock market provider.
5. Run `urgent_event_scan` against the demo lifecycle store.
6. Generate `reports/demo/daily_briefing_YYYYMMDD.md/json`.
7. Validate that `StreamlitDataLoader` can read demo EventCards, ReviewResults, RuleUpdates, lifecycle state, scheduler runs, and briefing reports.
8. Optionally write `reports/demo/full_demo_summary_YYYYMMDD.md/json`.

## Boundaries

The full demo is deterministic and offline. It does not fetch news, call DeepSeek or any LLM, change the ledger schema, start a scheduler daemon, send push notifications, or perform trading actions. Mock/demo results are labeled as demonstration data and should not be treated as real market evidence.

Risk disclaimer: 本内容仅用于事件研究和市场分析，不构成投资建议。
