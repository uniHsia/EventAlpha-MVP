# Phase 3C LLM Causal Reasoning

## Why Phase 3C Is Safe Now

Phase 3B.7 made LLM extraction pass the current gold-set gate: event type, status, entities, asset hints, and downstream alert behavior are stable enough to provide a structured input for causal reasoning.

This phase only makes causal reasoning optionally LLM-backed. The default pipeline still uses the deterministic rule-based causal chain.

## Why Anti-Spurious Stays Rule-Based

Anti-spurious checking is the control layer that challenges the causal chain. Replacing both causal reasoning and anti-spurious at the same time would remove the system's independent critique. Phase 3C therefore replaces only the chain generator when explicitly enabled.

## LLMCausalReasoningAgent

Input:

- `StructuredEvent`
- optional `EventVerification`
- optional `ImpactScore`
- optional supported assets
- optional extraction warnings

Output:

- validated `CausalChain`

The agent forces `event_id` to the structured event's ID and regenerates `chain_id` / `created_at`. LLM-provided internal audit fields are not trusted.

## Supported Assets Guardrail

LLM `affected_assets` are normalized and filtered against:

- `StructuredEvent.affected_assets_hint`
- asset alias standard names
- `asset_mapping_seed.yaml`
- any explicit `supported_assets`

Unsupported assets are filtered with warnings. They are not silently passed into ledger-facing downstream steps.

## Strict And Fallback Modes

- `strict`: invalid JSON, schema failure, unsupported-only assets, or other LLM failures raise.
- `fallback`: failures return the rule-based causal chain and expose `causal_warnings`.

## Rumor And Low-Verification Confidence

If the event is a rumor or verification is weak, LLM causal confidence is capped at `0.55`. If extraction warnings are numerous, confidence is capped at `0.65`.

## Running

```bash
python scripts/run_llm_causal_pipeline.py
python scripts/run_llm_causal_pipeline.py --real-llm --failure-mode fallback
python scripts/run_llm_causal_pipeline.py --real-llm --use-llm-extraction --failure-mode fallback
python scripts/evaluate_llm_causal_reasoning.py
python scripts/evaluate_llm_causal_reasoning.py --real-llm --write-report
```

## Evaluation Metrics

- `affected_assets_overlap_avg`
- `variable_type_coverage_avg`
- `direction_match_count`
- `confidence_delta_avg`
- `unsupported_asset_count`
- `too_long_chain_count`
- `low_confidence_for_rumor_count`
- `causal_warning_count`
- `failed_case_count`

The evaluation is an engineering quality check. LLM chains do not need to exactly match the rule-based chains, but they must not invent unsupported assets or assign high confidence to weak/rumor inputs.

All outputs are for event research and market analysis only. They do not constitute investment advice.
