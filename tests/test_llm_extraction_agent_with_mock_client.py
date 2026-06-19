"""Tests for the LLM extraction demo helper."""

from __future__ import annotations

import json
from pathlib import Path

from eventalpha.llm import MockLLMClient
from eventalpha.schemas import StructuredEvent, RawNews
from scripts.run_llm_extraction_demo import run_llm_extraction


def test_llm_extraction_demo_with_mock_client(tmp_path) -> None:
    """Mock LLM extraction should validate without writing a ledger DB."""
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    raw_news = RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[0])

    event = run_llm_extraction(raw_news, MockLLMClient(), trace_dir=tmp_path)

    assert isinstance(event, StructuredEvent)
    assert event.event_type == "ai_export_control"
    assert not (tmp_path / "eventalpha_mvp.sqlite3").exists()
    assert list(tmp_path.glob("*.jsonl"))

