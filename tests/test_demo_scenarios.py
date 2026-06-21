"""Tests for deterministic full-demo scenarios."""

from __future__ import annotations

import pytest

from eventalpha.demo.demo_scenarios import (
    contains_forbidden_trading_terms,
    get_demo_scenario,
    list_demo_scenarios,
)


def test_ai_export_control_scenario_loads() -> None:
    scenario = get_demo_scenario("ai_export_control")

    assert scenario.scenario_id == "ai_export_control"
    assert scenario.event_type == "ai_export_control"
    assert scenario.review_horizon == "T+1"
    assert scenario.raw_news.source == "Reuters / Mock Global News"


def test_ai_export_control_scenario_has_five_assets() -> None:
    scenario = get_demo_scenario()

    assert scenario.expected_assets == ["国产 AI 芯片", "服务器", "先进封装", "国产 EDA", "半导体设备"]
    assert len(scenario.mock_review_returns) == 5


def test_scenario_text_has_no_trading_instruction_terms() -> None:
    scenario = get_demo_scenario()
    text = " ".join(
        [
            scenario.title,
            scenario.raw_news.raw_text,
            " ".join(scenario.expected_assets),
            " ".join(scenario.notes),
        ]
    )

    assert not contains_forbidden_trading_terms(text)


def test_reserved_scenario_errors_are_clear() -> None:
    assert "rate_policy" in list_demo_scenarios()
    with pytest.raises(ValueError, match="reserved"):
        get_demo_scenario("rate_policy")
