"""Tests for the single-event analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RISK_DISCLAIMER, RawNews
from eventalpha.services import LedgerService


def _load_demo_event() -> RawNews:
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    return RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[0])


def test_ai_export_control_event_runs_full_pipeline(tmp_path) -> None:
    """AI chip export-control news should produce all MVP artifacts."""
    ledger = LedgerService(tmp_path / "eventalpha_test.sqlite3")
    result = run_event_pipeline(_load_demo_event(), ledger_service=ledger)

    assert result["structured_event"].event_type == "ai_export_control"
    assert result["verification"].credibility_score > 0
    assert result["impact_score"].impact_score > 0
    assert result["causal_chain"].logic
    assert result["anti_spurious_check"].spurious_risk in {"low", "medium", "high"}
    assert result["market_mapping"].mapped_assets
    assert RISK_DISCLAIMER in result["event_card"].risk_disclaimer
    assert result["prediction_ledger_entry"].predicted_assets
    assert len(result["review_tasks"]) == 3
