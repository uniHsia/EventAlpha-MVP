# Phase 3B.6: Extraction Gold Set and Downstream Calibration

Phase 3B.6 adds a hand-written extraction gold set and lightweight calibration for LLM extraction. It does not replace the causal reasoning, anti-spurious, review, provider, or ledger flows.

## Why Rule-Based Is Not Gold

The rule-based extractor is deterministic and useful as a baseline, but it is not a ground truth label source. It may miss flexible wording, overfit to keywords, or assign event times from publish time. The gold set is a small manually written engineering benchmark used to decide whether LLM extraction is safe enough to feed more downstream agents.

## Gold Set

Gold cases live in:

```text
eventalpha/examples/extraction_gold_cases.json
```

Each case has raw news fields and a `gold` object with expected event type, status, entities, locations, industries, asset hints, novelty range, expected event level, and expected trigger behavior.

Current `EventType` remains unchanged. Unsupported categories such as `technology_breakthrough`, `election_policy`, and `company_event` are recorded in `case_category` and notes, while the schema field uses `unknown`.

## Calibration

`LLMExtractionAgent` now runs lightweight calibration by default:

- status calibration checks whether raw text signals `announced`, `happened`, `rumor`, or a watch-only condition;
- entity normalization uses `entity_aliases.yaml`;
- industry normalization uses `industry_aliases.yaml`;
- asset normalization remains separate and uses `asset_aliases.yaml`;
- novelty calibration prevents important events from being downgraded by an overly low model novelty score.

Calibration can be disabled with `enable_calibration=False` when constructing `LLMExtractionAgent`.

## Novelty Rules

The first version keeps novelty simple:

- if LLM and rule-based novelty differ by more than `0.25`, record a warning;
- use `max(llm_novelty, rule_based_novelty * 0.9)`;
- apply a `0.6` floor for high-impact event types: `ai_export_control`, `geopolitical_conflict`, `rate_policy`, and `trade_tariff`.

All changes are recorded in extraction warnings.

## Downstream Consistency

Extraction quality is not only a schema issue. The downstream evaluator checks whether extraction changes alter:

- `impact_score`;
- `event_level`;
- `trigger_alert`;
- `tracking_mode`;
- `mapped_assets`;
- `review_schedule`.

Severe regression is flagged when a high-level gold event becomes low-level, a required alert disappears, mapped asset overlap is too low, or impact score diverges too far from the rule-based baseline.

## Readiness Gate

`ready_for_phase3c` requires:

- `event_type_accuracy >= 0.90`;
- `status_accuracy >= 0.75`;
- `asset_hint_recall_avg >= 0.65`;
- `entity_recall_avg >= 0.50`;
- `suspicious_event_time_count == 0`;
- `failed_case_count == 0`;
- `severe_downstream_regression_count == 0`.

If the gate fails, improve prompts, aliases, or calibration before replacing CausalReasoningAgent.

## Commands

Offline gold evaluation:

```bash
python scripts/evaluate_llm_extraction_gold.py
```

Offline downstream evaluation:

```bash
python scripts/evaluate_extraction_downstream.py
```

Real DeepSeek / OpenAI-compatible evaluation:

```bash
python scripts/evaluate_llm_extraction_gold.py --real-llm --calibrated --write-report
python scripts/evaluate_extraction_downstream.py --real-llm --calibrated --write-report
```

Reports are written to:

```text
reports/llm_extraction_gold_eval.json
reports/llm_extraction_gold_eval.md
reports/extraction_downstream_eval.json
reports/extraction_downstream_eval.md
```

## Compliance

These evaluations are only for event research and market analysis. They do not provide buy, sell, target price, guaranteed return, leverage advice, or automatic trading instructions.

