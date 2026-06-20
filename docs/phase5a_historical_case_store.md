# Phase 5A Historical Case Store

Phase 5A adds a small offline historical case store for EventAlpha. It supports the research workflow of comparing a current event with past similar events and reviewing illustrative market outcomes and causal lessons.

This phase does not change the Prediction Ledger schema, does not call an LLM, does not use embeddings or a vector database, and does not provide investment advice.

## Why After Phase 4D

Phase 4D can track event lifecycle state across news scout runs. Phase 5A adds a memory layer: once an event is tracked, analysts can ask whether similar historical events existed and what causal assumptions were useful or misleading.

## Schemas

`HistoricalCase` stores the historical event title, type, date, region, summary, entities, industries, affected assets, causal chain summary, source notes, tags, outcome, and causal assessment.

`HistoricalOutcome` stores illustrative market reaction information:

- benchmark
- asset_returns
- market_reaction_summary
- time_windows
- outcome_quality

`HistoricalCausalAssessment` stores the expected and realized direction, causal validity, what worked, what failed, and lessons.

## Seed Cases

The seed cases are MVP demo data. They are manually written illustrative examples and are not verified investment returns. They cover AI chip export controls, Middle East oil risk, central bank rate cuts, Fed holds, tariff policy, earthquake supply-chain shocks, technology breakthroughs, Red Sea shipping attacks, election policy shifts, and cloud AI capex.

Later phases can replace or augment these examples with real ledger reviews and market data.

## Case Store

The JSON store defaults to:

```bash
data/historical_cases.json
```

The file is ignored by git. Tests use temporary paths. The store supports load, save, upsert, get, list, and reset.

## Case Search

The first search version is deterministic and offline. It scores:

- exact `event_type` match
- affected asset overlap
- entity overlap
- tag overlap
- query keyword overlap

It does not use embeddings, RAG, or LLM calls.

## Current Event Helpers

Use these helpers to search from current EventAlpha objects:

```python
search_cases_for_tracked_event(cases, tracked_event, limit=5)
search_cases_for_structured_event(cases, event, limit=5)
```

They extract title, summary, claims, entities, affected assets, and event type into the same rule-based search.

## Commands

Run with in-memory seed cases:

```bash
python scripts/run_historical_case_demo.py
```

Write seed cases to the JSON store:

```bash
python scripts/run_historical_case_demo.py --seed
```

Search:

```bash
python scripts/run_historical_case_demo.py --query "AI chip export control"
python scripts/run_historical_case_demo.py --event-type ai_export_control
```

## Future Phases

Phase 5B can improve analogy retrieval and explanation. Phase 5C can connect real market outcomes, ledger reviews, or curated historical datasets.

## Risk Notice

This system is for event research and market analysis only. It does not provide investment advice, trading instructions, target prices, or buy/sell recommendations.
