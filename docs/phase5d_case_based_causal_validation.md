# Phase 5D Case-Based Causal Validation

Phase 5D turns Phase 5B analogies and Phase 5C outcome comparisons into deterministic causal-validation metadata. Phase 5C.1 compares outcome windows; Phase 5D asks whether historical lessons and outcome signals support, weaken, or require verification of the current causal chain and asset mapping.

This phase is fully offline. It does not call LLMs, use embeddings or RAG, fetch real market data, run a scheduler, build UI, write Prediction Ledger rows, or change ledger schema.

## Schemas

`CausalValidationSignal` stores one case-level signal: signal type, strength, source case metadata, affected chain steps, related assets, reliability, rationale, and risk notes.

`AssetLevelHistoricalSignal` stores one mapped-asset summary: historical support label, clamped support score, supporting or weakening cases, lessons, required verifications, and reliability.

`CaseBasedCausalValidation` stores the event-level result: current event title, event type, overall validation, confidence adjustment hint, case signals, asset signals, transferable and non-transferable lessons, required verifications, validation notes, and risk notes.

## Validator Rules

The validator consumes `StructuredEvent`, `CausalChain`, optional `MarketMapping`, `HistoricalAnalogy` rows, and `HistoricalOutcomeComparison` rows.

No analogies produce `insufficient_history`. Strong or moderate analogies with comparable outcome comparisons produce `supports_chain`. Mixed outcome comparisons produce `requires_verification`, while fully opposite comparable windows can produce `weakens_chain`.

Historical lessons containing pricing, priced-in, or rumor language produce `priced_in_risk`. Lessons mentioning second-order mapping, equipment, EDA, capex, orders, backlog, or supplier commentary can produce `second_order_warning` when the current chain or mapped assets contain related concepts.

Asset-level signals compare each mapped asset against analogy matched terms, similarities, lessons, case titles, and current chain assets. `second_order_watch` mapped assets remain watch signals when history also says verification is needed.

## Confidence Hint

`confidence_adjustment_hint` is only metadata. It never mutates `CausalChain.confidence`, EventCard confidence, anti-spurious confidence, or Prediction Ledger rows.

Conservative defaults:

- strong non-demo support: up to `+0.05`
- demo-only support: up to `+0.02`
- mixed/inconclusive: around `-0.03`
- weakened chain: around `-0.05`
- insufficient history: `0.0`

## Reliability

Reliability is inherited from outcome comparisons:

- `demo_only`: manual seed or mock outcome signal; illustrative only.
- `insufficient`: no usable current or historical outcome signal.
- `preliminary`: useful review signal but not fully verified.
- `review_backed`: verified history plus ledger review data.
- `market_backed`: verified history plus market-provider data.

Manual seed and mock demo comparisons must not be treated as real market evidence.

## Future Integration

Later phases can attach validation summaries to EventCard metadata, AntiSpuriousCheck notes, or PredictionLedger metadata without changing the core ledger schema. Phase 5D deliberately keeps validation as a separate history-layer artifact so downstream integration can be reviewed separately.

## Risk Notice

Case-based causal validation is for event research and market analysis only. It does not provide investment advice, trading instructions, target prices, or buy/sell recommendations.
