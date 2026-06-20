# Phase 5B Historical Analogy Retrieval

Phase 5B builds on the Phase 5A Historical Case Store. Phase 5A can find related cases; Phase 5B explains why a case is analogous, where the analogy is weak, which lessons can transfer, and what still needs verification.

This phase is fully offline. It does not use LLMs, embeddings, vector databases, RAG, scheduling, UI, trading, or ledger schema changes.

Phase 5B.1 adds context-completeness diagnostics, strength labels, low-score explanations, event-family-specific verification suggestions, and richer demo inputs. See `docs/phase5b1_analogy_context_calibration.md`.

## HistoricalAnalogy Schema

`AnalogyDimensionScore` stores a score for one similarity dimension:

- dimension
- score
- matched_terms
- explanation

`HistoricalAnalogy` stores the overall result:

- current event title
- historical case ID and title
- overall score
- dimension scores
- similarities
- differences
- transferable lessons
- non-transferable lessons
- verification suggestions
- risk notes

## Dimensions

The first version uses deterministic dimensions:

- `event_type`
- `affected_assets`
- `entities`
- `industries`
- `tags`
- `causal_chain`
- `query_keywords`
- `region`

`outcome_pattern` is intentionally not a high-weight score dimension because Phase 5A seed outcomes are illustrative demo data, not verified return studies.

## Scoring

The retriever uses lowercase token overlap and exact matching:

- event type and region use exact normalized match.
- assets, entities, industries, tags, causal chain, and query use Jaccard overlap.
- scores are weighted and normalized to `0..1`.
- results are sorted by `overall_score`.

No model calls or network access are used.

## Explanation

The explainer outputs:

- why the historical case is similar
- key differences
- transferable lessons
- non-transferable lessons
- verification suggestions
- risk notes

The explanation always preserves the non-investment-advice boundary.

## Demo Commands

```bash
python scripts/run_historical_analogy_demo.py
python scripts/run_historical_analogy_demo.py --query "AI chip export control"
python scripts/run_historical_analogy_demo.py --event-type ai_export_control
python scripts/run_historical_analogy_demo.py --asset "AI chips"
python scripts/run_historical_analogy_demo.py --demo-current-ai-export
python scripts/run_historical_analogy_demo.py --from-active-event 1
```

If `data/historical_cases.json` exists, the demo reads it. Otherwise it uses in-memory MVP seed cases.

## Future Phases

Phase 5C can compare historical outcomes with real market data or ledger review results. Phase 5D can add curated case-quality controls and stronger analogy diagnostics. Those phases should still preserve the non-investment-advice boundary.

## Risk Notice

Historical analogies are research aids only. They do not provide investment advice, trading instructions, target prices, or buy/sell recommendations. Seed outcomes are illustrative examples and are not verified market returns.
