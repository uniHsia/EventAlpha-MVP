# Phase 3A: LLM Structured Output

Phase 3A adds the LLM access layer without replacing the existing mock agents. The goal is to make future LLM agents safe to plug in: every model output must be validated against a Pydantic schema before business code can use it.

## Why LLMClient First

The current pipeline is already auditable: event extraction, ledger writing, review, and rule updates all use typed schemas. Replacing agents directly with free-form LLM calls would weaken that boundary. `LLMClient` keeps the contract simple: a prompt plus a Pydantic schema returns a validated Pydantic object, never a raw natural-language string.

## Structured Output Boundary

`schema_utils.pydantic_to_json_schema()` turns existing Pydantic models into JSON Schema for prompts and OpenAI-compatible response formats. The model output is then parsed and validated by Pydantic. Unknown fields, invalid Literal values, bad JSON, and wrong types are rejected.

`StructuredRunner` adds bounded retry and repair. If validation fails, it asks the model to return only schema-valid JSON and includes the validation error summary. Retries are finite.

## Clients

- `MockLLMClient`: deterministic, offline, used by tests and the default demo.
- `OpenAICompatibleLLMClient`: uses the OpenAI Python SDK with `api_key`, `base_url`, and `model`, so it can work with OpenAI, DeepSeek, Qwen / Alibaba Cloud Bailian, and other OpenAI-compatible APIs.

## Environment

Put real keys only in local `.env`. Do not commit `.env`.

DeepSeek example:

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

Qwen / Alibaba Cloud Bailian example:

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus
```

OpenAI example:

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
```

## Demo

Default offline demo:

```bash
python scripts/run_llm_extraction_demo.py
```

Real LLM demo:

```bash
python scripts/run_llm_extraction_demo.py --real-llm
python scripts/run_llm_extraction_demo.py --real-llm --base-url https://api.deepseek.com --model deepseek-chat
```

If `OPENAI_API_KEY` or `OPENAI_MODEL` is missing, the real demo prints a clear configuration error and exits without affecting the default mock pipeline.

## Trace

LLM traces are written as JSONL to:

```text
data/llm_traces/YYYYMMDD.jsonl
```

Trace records include timestamp, model, provider base URL, prompt name, schema name, success, validation error, retry count, and raw output preview. API keys are never recorded.

## Testing

`pytest` defaults to offline tests using `MockLLMClient`. The optional live LLM integration test is skipped unless `EVENTALPHA_RUN_LIVE_LLM=1` and a valid API key are configured.

## Compliance

LLM outputs are only used for event research and market analysis. They must not output buy, sell, target price, guaranteed return, leverage advice, or automatic trading instructions.
