"""Tests for LLMExtractionAgent strict and fallback behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eventalpha.agents import LLMExtractionAgent
from eventalpha.llm import LLMOutputValidationError, LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService


def _raw_news() -> RawNews:
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    return RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[0])


def _bad_runner(tmp_path) -> StructuredRunner:
    return StructuredRunner(
        MockLLMClient(responses={"StructuredEvent": "{bad json"}),
        trace_writer=LLMTraceWriter(tmp_path, enabled=True),
    )


def test_strict_mode_raises_validation_error(tmp_path) -> None:
    """Strict mode should not hide invalid LLM output."""
    agent = LLMExtractionAgent(runner=_bad_runner(tmp_path), failure_mode="strict")

    with pytest.raises(LLMOutputValidationError):
        agent.extract(_raw_news())


def test_fallback_mode_uses_rule_based_extraction(tmp_path) -> None:
    """Fallback mode should return rule-based output and record a warning."""
    raw_news = _raw_news()
    agent = LLMExtractionAgent(runner=_bad_runner(tmp_path), failure_mode="fallback")

    event = agent.extract(raw_news)

    assert event.raw_id == raw_news.raw_id
    assert event.event_type == "ai_export_control"
    assert agent.warnings
    assert "fell back to rule-based" in agent.warnings[0]


def test_fallback_mode_can_continue_full_pipeline(tmp_path) -> None:
    """Pipeline should continue after LLM extraction fallback."""
    agent = LLMExtractionAgent(runner=_bad_runner(tmp_path / "traces"), failure_mode="fallback")

    result = run_event_pipeline(
        _raw_news(),
        ledger_service=LedgerService(tmp_path / "eventalpha_test.sqlite3"),
        extraction_agent=agent,
    )

    assert result["structured_event"].event_type == "ai_export_control"
    assert result["prediction_ledger_entry"].predicted_assets
    assert result["extraction_warnings"]

