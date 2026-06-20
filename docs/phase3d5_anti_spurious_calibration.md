# Phase 3D.5 Anti-Spurious Calibration And Critique Compression

## Why Phase 3D.5 Exists

Phase 3D proved that the optional LLM anti-spurious critic can pass a real DeepSeek quality gate without becoming overconfident on rumor or weak-evidence cases. The next issue is usability: a critic that marks every case as medium/high risk and emits long critique lists can become noisy once we connect real news flow.

Phase 3D.5 keeps the same safety boundary but makes the critic more practical for downstream event cards and future news ingestion.

## Why Not Every Case Should Be Medium Or High

If the system treats all short-chain, high-credibility, directly-mapped events as medium/high risk, the critic stops helping with prioritization. That creates two problems:

- Event cards become long and repetitive.
- Real news flow will accumulate too many medium/high warnings even when the event is direct, credible, and already bounded by supported assets.

Phase 3D.5 therefore allows a conservative downgrade path for obvious direct events, while still keeping rumor, warning-heavy, second-order, or evidence-light cases from becoming too confident.

## Risk Calibration Rules

The new `AntiSpuriousCalibrationService` applies only to LLM anti-spurious outputs.

Downgrade eligibility:

- `StructuredEvent.status` is `announced` or `happened`.
- `EventVerification.verification_status` is `high_confidence` or `confirmed`.
- `credibility_score >= 0.65`.
- `len(causal_chain.logic) <= 4`.
- No unsupported asset mentions appear in `issues` or `required_verifications`.
- No severe issue concepts appear in the critique.
- Active chain assets stay within `affected_assets_hint` / supported assets.
- `adjusted_confidence >= 0.55`.

Conservative floor conditions:

- `status=rumor`.
- low-verification statuses: `needs_confirmation`, `low_confidence`, `rumor`.
- warning-heavy cases: `len(extraction_warnings) + len(causal_warnings) >= 3`.
- second-order or watch-only assets appear in the active chain mapping.
- `required_verifications` is empty after repair.
- critique explicitly flags priced-in risk, insufficient evidence, too-far mapping, second-order watch assets, over-optimistic direction, or direct-jump / long-chain reasoning.
- `len(causal_chain.logic) > 5`.

Calibration is single-step only:

- `medium -> low`
- `high -> medium`
- never `high -> low`

Every applied calibration is written into `anti_spurious_warnings` with the stable prefix `anti_spurious calibration applied:`.

## Critique Compression Rules

The new `CritiqueCompressionService` compresses only the LLM anti-spurious critique itself.

Issues:

- Deduplicate by concept, not only exact string.
- Rank by severity.
- Keep at most 5.
- Prefer: insufficient evidence, priced-in, unsupported / too-far asset mapping, second-order watch assets, direct-jump / long-chain issues.
- Drop empty or generic filler when more specific critique exists.

Required verifications:

- Deduplicate by concept.
- Keep at most 5.
- Prefer: official evidence, order / bidding / capex / production signals, mapping validation, macro confirmation signals.
- Drop generic “follow up” reminders when more specific verification text exists.

## EventCard Compaction

Event card compaction is presentation-only and applies to all EventCards, including rule-based fallback results.

- `risk_factors` is capped at 6.
- `verification_indicators` is capped at 8.
- Existing verification / policy risk flags are preserved first.
- The most important anti-spurious issues and required verifications are merged in after deduplication and ranking.

This keeps cards readable without changing any schema or ledger payload shape.

## New Evaluation Metrics

`scripts/evaluate_llm_anti_spurious.py` now reports:

- `low_risk_count`
- `medium_risk_count`
- `high_risk_count`
- `issue_count_after_compression_avg`
- `required_verification_count_after_compression_avg`
- `max_issue_count`
- `max_required_verification_count`
- `risk_calibration_count`
- `event_card_risk_factor_count_avg`
- `event_card_verification_indicator_count_avg`

The evaluator also keeps the original safety metrics and records soft balance notes when low-risk cases do not appear or when high-risk cases dominate the set.

## Offline And Real-LLM Runs

Offline defaults:

```bash
pytest
python scripts/run_demo_event.py
python scripts/run_llm_anti_spurious_pipeline.py
python scripts/evaluate_llm_anti_spurious.py
```

Manual real DeepSeek / OpenAI-compatible recheck:

```bash
python scripts/run_llm_anti_spurious_pipeline.py --real-llm --failure-mode fallback
python scripts/run_llm_anti_spurious_pipeline.py --real-llm --use-llm-extraction --use-llm-causal --failure-mode fallback
python scripts/evaluate_llm_anti_spurious.py --real-llm --write-report
```

## Risk Warning

This system is for event research and market analysis only. It does not provide investment advice, buy/sell instructions, target prices, guaranteed returns, leverage guidance, or automated trading decisions.
