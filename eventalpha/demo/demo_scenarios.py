"""Deterministic offline demo scenarios."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from pydantic import Field, model_validator

from eventalpha.schemas import RawNews
from eventalpha.schemas.base import EventAlphaModel, utc_now


SUPPORTED_SCENARIOS = (
    "ai_export_control",
    "rate_policy",
    "geopolitical_oil",
    "trade_tariff",
    "earthquake_supply_chain",
)

FORBIDDEN_TRADING_TERMS = ("买入", "卖出", "目标价")


class DemoScenario(EventAlphaModel):
    """One deterministic demo setup."""

    scenario_id: str
    title: str
    raw_news: RawNews
    event_type: str
    expected_assets: list[str] = Field(default_factory=list)
    review_horizon: str = "T+1"
    source_label: str = "Reuters / Mock Global News"
    mock_review_returns: dict[str, dict[str, Any]] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_demo_text(self) -> "DemoScenario":
        """Keep demo copy inside the research-only boundary."""
        assert_no_trading_terms(
            " ".join(
                [
                    self.scenario_id,
                    self.title,
                    self.raw_news.title,
                    self.raw_news.raw_text,
                    " ".join(self.expected_assets),
                    " ".join(self.notes),
                ]
            )
        )
        return self


def get_demo_scenario(scenario_id: str = "ai_export_control") -> DemoScenario:
    """Return a deterministic scenario by id."""
    if scenario_id != "ai_export_control":
        if scenario_id in SUPPORTED_SCENARIOS:
            raise ValueError(f"Demo scenario is reserved but not implemented yet: {scenario_id}")
        raise ValueError(f"Unsupported demo scenario: {scenario_id}")
    now = utc_now() - timedelta(minutes=10)
    raw_news = RawNews(
        title="美国宣布升级 AI 芯片出口管制",
        source="Reuters / Mock Global News",
        source_type="mainstream_media",
        publish_time=now,
        language="zh",
        url="mock://eventalpha/demo/ai-export-control",
        raw_text=(
            "Reuters / Mock Global News 离线演示消息：美国宣布升级针对中国的 AI 芯片和先进 GPU "
            "出口管制。该事件可能影响海外 GPU 供应，并提升国产 AI 芯片、服务器、先进封装、"
            "国产 EDA 和半导体设备的研究关注度。本消息为 deterministic mock/demo 数据，"
            "仅用于演示 EventAlpha 的事件研究、因果分析、复盘和规则更新闭环。"
        ),
        metadata={
            "scenario_id": "ai_export_control",
            "demo_only": "true",
            "event_type_hint": "ai_export_control",
        },
    )
    return DemoScenario(
        scenario_id="ai_export_control",
        title="AI 芯片出口管制离线演示",
        raw_news=raw_news,
        event_type="ai_export_control",
        expected_assets=["国产 AI 芯片", "服务器", "先进封装", "国产 EDA", "半导体设备"],
        review_horizon="T+1",
        mock_review_returns={
            "国产 AI 芯片": {"direction": "correct", "excess_return": "positive"},
            "服务器": {"direction": "correct", "excess_return": "positive"},
            "先进封装": {"direction": "correct", "excess_return": "positive"},
            "国产 EDA": {"direction": "not_verified", "note": "mock T+1 return is flat"},
            "半导体设备": {"direction": "mixed/watch", "note": "second-order mapping"},
        },
        notes=[
            "默认离线，不联网，不调用 LLM。",
            "mock/demo 数据仅用于展示系统闭环，不代表真实市场证据。",
        ],
    )


def list_demo_scenarios() -> list[str]:
    """Return all known scenario ids."""
    return list(SUPPORTED_SCENARIOS)


def assert_no_trading_terms(value: str) -> None:
    """Raise when demo text contains disallowed trading instruction terms."""
    if contains_forbidden_trading_terms(value):
        raise ValueError("Demo scenario text contains disallowed trading instruction wording.")


def contains_forbidden_trading_terms(value: str) -> bool:
    """Return True when text contains forbidden trading instruction wording."""
    return any(term in value for term in FORBIDDEN_TRADING_TERMS)
