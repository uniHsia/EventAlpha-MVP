# Phase 5C Historical Outcome Comparison

Phase 5C builds on Phase 5B.1. Phase 5B.1 explains why a historical case is analogous; Phase 5C compares the historical outcome windows with available current review or market-return results.

This phase is fully offline. It does not call LLMs, does not use embeddings or RAG, does not run a scheduler, does not build UI, and does not change ledger schema.

## Not A Full Event Study

The first version is a deterministic comparison helper, not an academic event study. It does not estimate abnormal returns, calculate statistical significance, or control for broad factor models. It only compares simple T+1/T+3/T+7 outcome windows.

## OutcomeWindowComparison

`OutcomeWindowComparison` stores one window:

- `window`
- historical/current return
- historical/current excess return
- historical/current direction
- direction match
- excess-return sign match
- magnitude gap
- notes

Missing current or historical data is allowed and represented as `None`.

## HistoricalOutcomeComparison

`HistoricalOutcomeComparison` stores the case-level comparison:

- current event title
- historical case ID/title
- analogy score and strength
- outcome quality
- historical data quality
- current data quality
- comparison reliability
- mock scenario name, when applicable
- comparison status
- window comparisons
- matched lessons
- mismatch reasons
- validation notes
- risk notes

`outcome_quality` remains for backward compatibility. Newer reports should read `historical_data_quality`, `current_data_quality`, and `comparison_reliability` to understand whether a signal is demo-only, insufficient, preliminary, review-backed, or market-backed.

## Comparison Status

Statuses are:

- `missing_historical_outcome`: the historical case has no outcome data.
- `insufficient_current_outcome`: no current review or market outcome is available yet.
- `comparable`: most comparable windows point in the same direction.
- `mixed_or_inconclusive`: windows are mixed or incomplete.
- `historical_outcome_demo_only`: reserved for cases where downstream reporting wants to emphasize illustrative-only historical outcomes.

Status describes whether window-level directions can be compared. It does not claim data reliability. Reliability is expressed separately.

## Data Quality And Reliability

Phase 5C.1 adds explicit labels because Phase 5C comparisons can mix manual seed examples, mock current outcomes, future ledger reviews, and future market-provider returns.

Historical data quality labels:

- `manual_seed_demo`: deterministic illustrative seed numbers.
- `verified_backtest`: later verified historical outcome data.
- `ledger_review_derived`: later historical outcomes derived from ledger review artifacts.
- `unknown`: no quality source is known.

Current data quality labels:

- `missing`: no current outcome is available.
- `mock_demo`: deterministic demo current outcome, not real market data.
- `ledger_review`: current result came from ReviewResult-like review data.
- `market_provider`: current result came from market-return dictionaries.
- `unknown`: no quality source is known.

Comparison reliability labels:

- `insufficient`: missing historical or current outcome data.
- `demo_only`: manual seed plus mock/demo current outcome.
- `preliminary`: useful for research review, but not backed by verified historical data.
- `review_backed`: verified historical data plus ledger review data.
- `market_backed`: verified historical data plus market-provider outcome data.

## HistoricalOutcomeComparator

The comparator accepts:

- `HistoricalAnalogy`
- `HistoricalCase`
- optional `ReviewResult` objects or dict rows
- optional current market return dicts

It prefers current review results when they contain usable returns. Otherwise it reads simple market-return dictionaries. It averages returns by T+ window and compares directions and magnitude gaps.

Supported review rows include:

```python
{
    "horizon": "T+3",
    "asset_name": "国产 AI 芯片",
    "actual_return": 0.03,
    "benchmark_return": 0.01,
    "excess_return": 0.02,
}
```

and nested market-return rows:

```python
{
    "horizon": "T+3",
    "market_return": {
        "actual_return": 0.03,
        "benchmark_return": 0.01,
        "excess_return": 0.02,
    },
}
```

If multiple assets share the same horizon, returns are averaged. If `actual_return` and `benchmark_return` are present but `excess_return` is missing, the comparator computes excess return. Missing fields do not raise errors; they appear as window notes.

## Mock Current Outcome

The demo supports:

```bash
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome --mock-outcome-scenario aligned
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome --mock-outcome-scenario mixed
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome --mock-outcome-scenario opposite
```

This creates deterministic mock current outcomes so tests and demos can exercise the comparison path without network, LLM calls, market-data APIs, or ledger writes.

Scenarios:

- `aligned`: current demo returns broadly match historical direction.
- `mixed`: T+1 matches but later windows weaken or reverse.
- `opposite`: current demo returns move opposite to historical direction.

Mock current outcomes are deterministic demo data, not real market returns.

## Manual Seed Limitation

Phase 5A seed outcomes are `manual_seed_demo`. Phase 5C.1 gives them small non-zero return values so demos can show direction and magnitude behavior. These values are manual seed demo numbers only, not verified market returns or backtests. Any comparison using those outcomes must preserve this warning.

## Future Real Outcome Integration

Later phases can connect:

- real `ReviewResult` rows from Prediction Ledger review;
- provider-based market return calculations;
- ledger review summaries;
- higher-quality historical outcome datasets.

Those integrations should still keep schema compatibility and the non-investment-advice boundary.

## Phase 5D Usage

Phase 5D case-based causal validation can consume:

- `comparison_status` for direction-level behavior;
- per-window direction match and magnitude gaps;
- current and historical excess returns when available;
- `comparison_reliability` to decide whether a signal is demo-only, preliminary, review-backed, or market-backed.

Phase 5D should not treat `manual_seed_demo` or `mock_demo` comparisons as evidence of real market performance.

## Risk Notice

Historical outcomes are research references only. They do not provide investment advice, trading instructions, target prices, or buy/sell recommendations. Seed outcomes are illustrative examples and are not verified market returns.
