# Phase 3B.7 Entity Recall & Alert Calibration Fix

## Why This Phase Exists

Phase 3B.6 showed that LLM extraction can identify `event_type` reliably, but entity recall was still below the Phase 3C gate. That matters because downstream scoring, causal reasoning, and asset mapping all depend on extracted entities. If entities such as `关税`, `原油`, `黄金`, `供应链`, or `利率` are missed, later agents may produce weaker impact scores or miss alerts.

This phase does not replace the causal reasoning agent. It only improves extraction post-processing and downstream evaluation gates.

## Entity Keyword Completion

`eventalpha/rules/entity_keywords.yaml` defines event-type-specific keywords. The completion service only adds a keyword when it appears explicitly in the raw title or raw text. It does not infer hidden entities.

Rules:

- Match by direct substring and compact substring, so `AI芯片` can match `AI 芯片`.
- Add only missing keywords for the event's `event_type`.
- Normalize completed entities with `EntityNormalizationService`.
- Preserve unknown entities and record warnings instead of deleting them.

## Trade Tariff Alert Calibration

The scoring layer now applies a narrow alert floor for announced tariff escalation events:

- `event_type == trade_tariff`
- `status == announced`
- the event text includes escalation terms such as `加征关税`, `关税上调`, `进口商品`, or `贸易壁垒`

When these conditions hold, the event is kept at least at level `A`, `trigger_alert=True`, and `tracking_mode=enhanced`. Rumor-stage tariff talks, including `尚未落地` cases, are not force-upgraded.

## Gold-Based Alert Metrics

Downstream evaluation now separates rule-based differences from gold-label failures:

- `missed_alert_count`: gold expects alert, calibrated LLM does not alert.
- `over_alert_count`: gold does not expect alert, calibrated LLM alerts.
- `gold_event_level_mismatch_count`: calibrated LLM event level differs from gold expected level.
- `gold_trigger_alert_mismatch_count`: calibrated LLM alert flag differs from gold.

`event_level_changed_count` and `trigger_alert_changed_count` still measure differences from the rule-based pipeline only. They are diagnostic, not automatically bad.

## Phase 3C Gate

The intended gate remains:

- `event_type_accuracy >= 0.90`
- `status_accuracy >= 0.75`
- `entity_recall_avg >= 0.50`
- `asset_hint_recall_avg >= 0.65`
- `suspicious_event_time_count == 0`
- `failed_case_count == 0`
- `severe_downstream_regression_count == 0`
- `missed_alert_count == 0`

Run real DeepSeek validation manually:

```bash
python scripts/evaluate_llm_extraction_gold.py --real-llm --calibrated --write-report
python scripts/evaluate_extraction_downstream.py --real-llm --calibrated --write-report
```

All outputs are for event research and market analysis only. They do not constitute investment advice.
