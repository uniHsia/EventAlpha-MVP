"""Tests for MockLLMClient."""

from __future__ import annotations

import pytest

from eventalpha.llm import LLMOutputValidationError, MockLLMClient
from eventalpha.schemas import CausalChain, StructuredEvent


def test_mock_llm_client_returns_structured_event() -> None:
    """Default mock output should validate as StructuredEvent."""
    client = MockLLMClient()

    event = client.generate_structured("extract event", StructuredEvent)

    assert isinstance(event, StructuredEvent)
    assert event.event_type == "ai_export_control"


def test_mock_llm_client_uses_schema_name_specific_response() -> None:
    """Configured responses should be selected by schema class name."""
    client = MockLLMClient(
        responses={
            "StructuredEvent": {
                "event_type": "rate_policy",
                "event_title": "央行降息",
                "summary": "央行宣布降息。",
                "status": "announced",
            },
            "CausalChain": {
                "event_id": "EVT_TEST",
                "logic": [],
                "affected_assets": [],
                "direction": "mixed",
                "time_horizon": "T+3",
                "confidence": 0.5,
                "rationale": "test",
            },
        }
    )

    event = client.generate_structured("extract", StructuredEvent)
    chain = client.generate_structured("reason", CausalChain)

    assert event.event_type == "rate_policy"
    assert chain.event_id == "EVT_TEST"


def test_mock_llm_client_invalid_output_raises_validation_error() -> None:
    """Invalid mock output should raise the same validation error path as real output."""
    client = MockLLMClient(responses={"StructuredEvent": "{bad json"})

    with pytest.raises(LLMOutputValidationError):
        client.generate_structured("extract", StructuredEvent)


def test_mock_llm_client_missing_schema_raises_clear_error() -> None:
    """Missing mock fixtures should fail clearly."""
    client = MockLLMClient(responses={})

    with pytest.raises(LLMOutputValidationError, match="No mock LLM response"):
        client.generate_structured("extract", StructuredEvent)

