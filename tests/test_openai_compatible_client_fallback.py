"""Offline tests for OpenAI-compatible response_format fallback."""

from __future__ import annotations

from eventalpha.llm import LLMCallError, OpenAICompatibleLLMClient
from eventalpha.schemas import StructuredEvent


VALID_EVENT_JSON = """
{
  "event_type": "ai_export_control",
  "event_title": "美国宣布升级 AI 芯片出口管制",
  "summary": "出口管制更新。",
  "status": "announced"
}
"""


class FallbackClient(OpenAICompatibleLLMClient):
    """Fake client that never reaches the network."""

    def __init__(self, fail_json_object: bool = False) -> None:
        super().__init__(api_key="sk-test", base_url="https://example.test/v1", model="test-model")
        self.fail_json_object = fail_json_object
        self.calls: list[tuple[bool, bool]] = []

    def _call_chat_completion(
        self,
        prompt,
        schema,
        system_prompt,
        temperature,
        use_json_schema,
        include_response_format=True,
    ) -> str:
        self.calls.append((use_json_schema, include_response_format))
        if include_response_format and use_json_schema:
            raise LLMCallError("This response_format type is unavailable now")
        if include_response_format and self.fail_json_object:
            raise LLMCallError("response_format is unsupported")
        return VALID_EVENT_JSON


def test_falls_back_from_json_schema_to_json_object() -> None:
    """Provider json_schema errors should fall back to json_object."""
    client = FallbackClient()

    event = client.generate_structured("extract", StructuredEvent, max_retries=0)

    assert event.event_type == "ai_export_control"
    assert client.calls == [(True, True), (False, True)]


def test_falls_back_to_prompt_only_when_response_format_is_unavailable() -> None:
    """Providers without response_format support should still rely on Pydantic validation."""
    client = FallbackClient(fail_json_object=True)

    event = client.generate_structured("extract", StructuredEvent, max_retries=0)

    assert event.event_type == "ai_export_control"
    assert client.calls == [(True, True), (False, True), (False, False)]

