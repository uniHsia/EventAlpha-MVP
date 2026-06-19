"""Tests for run_llm_event_pipeline script helpers."""

from __future__ import annotations

from scripts.run_llm_event_pipeline import (
    build_llm_extraction_agent,
    load_demo_news,
    run_llm_event_pipeline,
)
from eventalpha.services import LedgerService


def test_run_llm_event_pipeline_helper_with_mock_client(tmp_path) -> None:
    """Script helper should run with MockLLMClient and no network."""
    raw_news = load_demo_news(0)
    agent = build_llm_extraction_agent(trace_dir=tmp_path / "traces")

    result = run_llm_event_pipeline(
        raw_news,
        extraction_agent=agent,
        ledger_service=LedgerService(tmp_path / "eventalpha_test.sqlite3"),
    )

    assert result["structured_event"].event_type == "ai_export_control"
    assert result["prediction_ledger_entry"].prediction_id
    assert list((tmp_path / "traces").glob("*.jsonl"))

