"""Tests for LLM extraction post-processing."""

from __future__ import annotations

from datetime import datetime, timezone

from eventalpha.agents import LLMExtractionAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.schemas import RawNews


def _raw_news() -> RawNews:
    return RawNews(
        raw_id="RAW_TEST_POSTPROCESS",
        title="美国宣布升级 AI 芯片出口管制",
        source="Reuters",
        source_type="mainstream_media",
        raw_text=(
            "Reuters 报道，美国宣布升级针对中国的 AI 芯片和先进 GPU 出口管制，"
            "国产 EDA 和服务器受到关注。"
        ),
        publish_time=datetime(2026, 6, 19, tzinfo=timezone.utc),
    )


def _agent_with_response(response: dict, tmp_path) -> LLMExtractionAgent:
    runner = StructuredRunner(
        MockLLMClient(responses={"StructuredEvent": response}),
        trace_writer=LLMTraceWriter(tmp_path, enabled=True),
    )
    return LLMExtractionAgent(runner=runner)


def test_postprocess_overwrites_internal_fields_and_raw_id(tmp_path) -> None:
    """LLM-created audit fields should be overwritten by the system."""
    response = {
        "event_id": "evt_20260619_001",
        "raw_id": "RAW_WRONG",
        "created_at": "2026-06-19T12:00:00Z",
        "event_type": "ai_export_control",
        "event_title": "美国宣布升级 AI 芯片出口管制",
        "summary": "出口管制升级。",
        "entities": ["美国"],
        "locations": ["美国", "中国"],
        "event_time": None,
        "status": "announced",
        "affected_industries": ["半导体"],
        "affected_assets_hint": ["AI芯片"],
        "novelty_score": 0.8,
    }

    event = _agent_with_response(response, tmp_path).extract(_raw_news())

    assert event.raw_id == "RAW_TEST_POSTPROCESS"
    assert event.event_id != "evt_20260619_001"
    assert event.event_id.startswith("EVT_")
    assert event.created_at.isoformat() != "2026-06-19T12:00:00+00:00"


def test_postprocess_clears_suspicious_event_time_and_normalizes_assets(tmp_path) -> None:
    """Suspicious model-generated times should be cleared and assets normalized."""
    response = {
        "raw_id": "RAW_WRONG",
        "event_type": "ai_export_control",
        "event_title": "美国宣布升级 AI 芯片出口管制",
        "summary": "出口管制升级。",
        "entities": ["美国"],
        "locations": ["美国", "中国"],
        "event_time": "2026-06-19T12:00:00Z",
        "status": "announced",
        "affected_industries": ["半导体"],
        "affected_assets_hint": ["AI芯片", "GPU", "EDA"],
        "novelty_score": 0.8,
    }
    agent = _agent_with_response(response, tmp_path)

    event = agent.extract(_raw_news())

    assert event.event_time is None
    assert event.affected_assets_hint == ["国产 AI 芯片", "国产 EDA"]
    assert any("event_time removed" in warning for warning in agent.warnings)
    assert any("normalized affected_assets_hint" in warning for warning in agent.warnings)


def test_postprocess_completes_entities_from_raw_text(tmp_path) -> None:
    """Keywords explicitly present in raw text should be added to entities."""
    response = {
        "raw_id": "RAW_WRONG",
        "event_type": "ai_export_control",
        "event_title": "美国宣布升级 AI 芯片出口管制",
        "summary": "出口管制升级。",
        "entities": ["美国"],
        "locations": ["美国", "中国"],
        "event_time": None,
        "status": "announced",
        "affected_industries": ["半导体"],
        "affected_assets_hint": ["AI芯片"],
        "novelty_score": 0.8,
    }
    agent = _agent_with_response(response, tmp_path)

    event = agent.extract(_raw_news())

    assert "AI 芯片" in event.entities
    assert "GPU" in event.entities
    assert "国产 EDA" in event.entities
    assert "服务器" in event.entities
    assert any("completed entities" in warning for warning in agent.warnings)
