"""Tests for LLM schema helpers."""

from __future__ import annotations

import pytest

from eventalpha.llm import (
    LLMOutputValidationError,
    pydantic_to_json_schema,
    schema_name,
    validate_structured_output,
)
from eventalpha.schemas import StructuredEvent


def test_pydantic_schema_contains_required_fields_and_literals() -> None:
    """StructuredEvent should produce a useful JSON Schema."""
    schema = pydantic_to_json_schema(StructuredEvent)

    assert schema_name(StructuredEvent) == "StructuredEvent"
    assert "event_type" in schema["properties"]
    assert "event_title" in schema["required"]

    event_type_schema = schema["properties"]["event_type"]
    assert "enum" in event_type_schema
    assert "ai_export_control" in event_type_schema["enum"]


def test_validate_structured_output_accepts_json_string() -> None:
    """Valid JSON should become a Pydantic model."""
    event = validate_structured_output(
        """
        ```json
        {
          "event_type": "ai_export_control",
          "event_title": "AI chip control",
          "summary": "Export control update",
          "status": "announced"
        }
        ```
        """,
        StructuredEvent,
    )

    assert event.event_type == "ai_export_control"
    assert event.event_title == "AI chip control"


def test_validate_structured_output_rejects_invalid_literal() -> None:
    """Literal violations should not be silently swallowed."""
    with pytest.raises(LLMOutputValidationError):
        validate_structured_output(
            {"event_type": "not_supported", "event_title": "bad"},
            StructuredEvent,
        )

