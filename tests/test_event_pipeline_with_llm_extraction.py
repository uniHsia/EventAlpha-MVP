"""Tests for event pipeline extraction-agent injection."""

from __future__ import annotations

import json
from pathlib import Path

from eventalpha.agents import LLMExtractionAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService


def _raw_news() -> RawNews:
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    return RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[0])


def test_event_pipeline_runs_with_llm_extraction(tmp_path) -> None:
    """Injected LLMExtractionAgent should only replace the extraction step."""
    agent = LLMExtractionAgent(
        runner=StructuredRunner(
            MockLLMClient(),
            trace_writer=LLMTraceWriter(tmp_path / "traces", enabled=True),
        )
    )

    result = run_event_pipeline(
        _raw_news(),
        ledger_service=LedgerService(tmp_path / "eventalpha_test.sqlite3"),
        extraction_agent=agent,
    )

    assert result["structured_event"].event_type == "ai_export_control"
    assert result["event_card"].event_id == result["structured_event"].event_id
    assert result["prediction_ledger_entry"].predicted_assets
    assert len(result["review_tasks"]) == 3
    assert result["extraction_warnings"] == []

