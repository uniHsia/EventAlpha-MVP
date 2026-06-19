# Phase 3B: LLM Event Extraction

Phase 3B adds an optional LLM-backed event extraction agent. The default EventAlpha pipeline still uses the rule-based extractor unless an extraction agent is explicitly injected or the LLM pipeline script is used.

## Why Event Extraction First

Event extraction has the clearest boundary: `RawNews` in, `StructuredEvent` out. It is the safest first LLM replacement because all downstream modules already consume typed Pydantic schemas.

## LLMExtractionAgent

`LLMExtractionAgent` renders `eventalpha/prompts/extraction_event.md`, calls `StructuredRunner`, and returns a validated `StructuredEvent`. It never returns raw text, dicts, or unvalidated JSON. The output `raw_id` is normalized to the input `RawNews.raw_id`.

## Rule-Based vs LLM Extraction

The rule-based extractor is deterministic and keyword-driven. LLM extraction can capture more flexible wording, but it can also fail schema validation or over-infer. Use `--compare-rule-based` to compare key fields:

```bash
python scripts/run_llm_event_pipeline.py --compare-rule-based
```

## Failure Modes

- `strict`: LLM extraction errors stop the pipeline.
- `fallback`: LLM extraction errors fall back to the rule-based extractor and expose a warning in the pipeline result.

## Running

Offline mock LLM:

```bash
python scripts/run_llm_event_pipeline.py
```

Real OpenAI-compatible LLM:

```bash
python scripts/run_llm_event_pipeline.py --real-llm
python scripts/run_llm_event_pipeline.py --real-llm --failure-mode fallback
python scripts/run_llm_event_pipeline.py --real-llm --base-url https://api.deepseek.com --model deepseek-chat
```

## Environment Examples

Put real keys only in local `.env`.

DeepSeek:

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

Qwen / Alibaba Cloud Bailian:

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus
```

OpenAI:

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
```

## Trace

LLM traces are written to:

```text
data/llm_traces/
```

The trace contains model, provider base URL, prompt name, schema name, success state, validation error, retry count, and output preview. API keys are never logged.

## Testing

`pytest` uses `MockLLMClient` by default and does not call real APIs. Optional live tests are skipped unless `EVENTALPHA_RUN_LIVE_LLM=1` and an API key are configured.

## Compliance

The system is only for event research and market analysis. It must not output buy, sell, target price, guaranteed return, leverage advice, or automatic trading instructions.
