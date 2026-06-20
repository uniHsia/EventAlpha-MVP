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
- comparison status
- window comparisons
- matched lessons
- mismatch reasons
- validation notes
- risk notes

## Comparison Status

Statuses are:

- `missing_historical_outcome`: the historical case has no outcome data.
- `insufficient_current_outcome`: no current review or market outcome is available yet.
- `comparable`: most comparable windows point in the same direction.
- `mixed_or_inconclusive`: windows are mixed or incomplete.
- `historical_outcome_demo_only`: reserved for cases where downstream reporting wants to emphasize illustrative-only historical outcomes.

## HistoricalOutcomeComparator

The comparator accepts:

- `HistoricalAnalogy`
- `HistoricalCase`
- optional `ReviewResult` objects or dict rows
- optional current market return dicts

It prefers current review results when available. Otherwise it reads simple market-return dictionaries. It averages returns by T+ window and compares directions and magnitude gaps.

## Mock Current Outcome

The demo supports:

```bash
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome
```

This creates deterministic mock current outcomes so tests and demos can exercise the comparison path without network, LLM calls, market-data APIs, or ledger writes.

## Manual Seed Limitation

Phase 5A seed outcomes are `manual_seed_demo`. They are illustrative examples only, not verified market returns or backtests. Any comparison using those outcomes must preserve this warning.

## Future Real Outcome Integration

Later phases can connect:

- real `ReviewResult` rows from Prediction Ledger review;
- provider-based market return calculations;
- ledger review summaries;
- higher-quality historical outcome datasets.

Those integrations should still keep schema compatibility and the non-investment-advice boundary.

## Risk Notice

Historical outcomes are research references only. They do not provide investment advice, trading instructions, target prices, or buy/sell recommendations. Seed outcomes are illustrative examples and are not verified market returns.
