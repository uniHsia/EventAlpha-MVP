# Phase 5D.1 Card / AntiSpurious Integration

Phase 5D produced case-based causal validation as a separate history-layer artifact. Phase 5D.1 makes that artifact visible in the EventCard and rule-based AntiSpurious explanation layers without changing the default pipeline contract or ledger schema.

This phase remains offline. It does not call LLMs, use embeddings or RAG, fetch market data, run schedulers, build UI, write Prediction Ledger rows from the history demo, or create trading instructions.

## HistoryValidationSummary

`HistoryValidationSummary` is a compact view derived from `CaseBasedCausalValidation`. It keeps only the fields needed by EventCard and AntiSpurious:

- `overall_validation`
- `confidence_adjustment_hint`
- `top_signals`
- `asset_notes`
- `transferable_lessons`
- `required_verifications`
- `risk_notes`
- `reliability`

The full validation object stays outside the card. Demo-only summaries always carry a warning that historical signals are illustrative and not real market evidence.

## EventCard Integration

`generate_event_card` accepts an optional `history_validation_summary`.

When present, the card:

- stores a transient `history_validation_summary` payload on the EventCard object;
- merges history risk notes and priced-in / second-order / weakened-chain signals into `risk_factors`;
- merges case-based required verifications and asset notes into `verification_indicators`;
- keeps existing compaction limits for card lists;
- does not change `one_sentence` or possible-impact confidence math.

The new EventCard field is runtime/card-output metadata. The SQLite ledger schema and EventCard persistence columns are unchanged.

## AntiSpurious Integration

The rule-based AntiSpurious checker accepts an optional summary.

When present:

- `second_order_warning` adds a history-backed issue;
- `priced_in_risk` adds a pricing-risk issue;
- `requires_verification` adds case-based required verifications;
- `historically_weakened` can raise risk conservatively.

If reliability is `demo_only`, weakening can raise low risk only to medium. Demo-only signals are notes for interpretation, not market evidence.

## Confidence And Reliability Boundary

`confidence_adjustment_hint` remains metadata. Phase 5D.1 does not mutate `CausalChain.confidence`, EventCard final confidence, PredictionLedger confidence, or formal review confidence.

Reliability labels:

- `demo_only`: manual seed or mock outcome signal, illustrative only.
- `insufficient`: not enough historical/current outcome evidence.
- `preliminary`: useful review signal but not fully verified.
- `review_backed`: verified history with ledger review data.
- `market_backed`: verified history with market-provider data.

## Demo

Run:

```bash
python scripts/run_event_with_history_validation_demo.py
python scripts/run_event_with_history_validation_demo.py --demo-current-ai-export
python scripts/run_event_with_history_validation_demo.py --demo-current-ai-export --mock-outcome-scenario aligned
python scripts/run_event_with_history_validation_demo.py --demo-current-ai-export --mock-outcome-scenario mixed
python scripts/run_event_with_history_validation_demo.py --demo-current-ai-export --mock-outcome-scenario opposite
```

The demo prints baseline versus enhanced EventCard and AntiSpurious outputs. Mock outcomes are deterministic demo data, not real market data.

## Next Phase

Phase 6A can add scheduler/orchestration once the card and critique layers can display historical validation safely. Any future PredictionLedger metadata integration should remain schema-reviewed separately.

## Risk Notice

These outputs are for event research and market analysis only. They do not constitute investment advice, trading instructions, target prices, or buy/sell recommendations.
