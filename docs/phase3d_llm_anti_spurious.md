# Phase 3D Optional LLM Anti-Spurious Critic

## Why After Phase 3C

Phase 3C made LLM causal reasoning usable behind an explicit flag. The next risk is that a cleaner LLM causal chain may be too simple and omit second-order watch assets, weak evidence, or required verification signals. Phase 3D adds an optional LLM critic without replacing the default rule-based anti-spurious layer.

## LLMAntiSpuriousAgent

Input:

- `StructuredEvent`
- `CausalChain`
- optional `EventVerification`
- optional `ImpactScore`
- optional `MarketMapping`
- extraction and causal warnings
- supported assets

Output:

- validated `AntiSpuriousCheck`

The agent forces `event_id` and `chain_id` from the input objects and regenerates `check_id` / `created_at`. LLM-provided internal audit fields are not trusted.

## Strict And Fallback

- `strict`: invalid JSON or schema failure raises.
- `fallback`: invalid LLM output returns the rule-based anti-spurious check and records `anti_spurious_warnings`.

## Confidence Guardrails

Rumor, low-verification, and warning-heavy cases cap `adjusted_confidence`. Empty critiques are warned, and issues without `required_verifications` are repaired with a generic verification request.

## Second-Order Watch Assets

The critic is expected to flag second-order or watch-only mappings, including overextended asset links and missing verification signals. Unsupported asset mentions are preserved as issues/warnings only; they do not enter ledger-facing asset lists.

## Running

```bash
python scripts/run_llm_anti_spurious_pipeline.py
python scripts/run_llm_anti_spurious_pipeline.py --real-llm --failure-mode fallback
python scripts/run_llm_anti_spurious_pipeline.py --real-llm --use-llm-extraction --use-llm-causal --failure-mode fallback
python scripts/evaluate_llm_anti_spurious.py
python scripts/evaluate_llm_anti_spurious.py --real-llm --write-report
```

## Evaluation Metrics

- `spurious_risk_distribution`
- `adjusted_confidence_delta_avg`
- `required_verification_count_avg`
- `issue_count_avg`
- `high_risk_for_rumor_count`
- `overconfident_rumor_count`
- `second_order_issue_detected_count`
- `missing_required_verification_count`
- `empty_critique_count`
- `failed_case_count`

The critic is allowed to be stricter than the rule-based checker. It must not provide investment advice or trading instructions.

All outputs are for event research and market analysis only. They do not constitute investment advice.
