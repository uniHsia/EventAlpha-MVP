"""Tests for LLM extraction prompt variables."""

from __future__ import annotations

import pytest

from eventalpha.llm import PromptTemplate


def test_extraction_prompt_supports_supported_asset_names() -> None:
    """The extraction prompt should render the supported asset vocabulary."""
    template = PromptTemplate.from_file("eventalpha/prompts/extraction_event.md")

    rendered = template.render(
        json_schema="{}",
        raw_title="demo",
        raw_text="demo text",
        source="Reuters",
        source_type="mainstream_media",
        publish_time="2026-06-19T00:00:00Z",
        supported_event_types="ai_export_control, unknown",
        supported_asset_names="国产 AI 芯片, 国产 EDA",
    )

    assert "supported_asset_names" in rendered
    assert "国产 AI 芯片" in rendered


def test_extraction_prompt_missing_supported_asset_names_raises() -> None:
    """Missing supported_asset_names should fail fast."""
    template = PromptTemplate.from_file("eventalpha/prompts/extraction_event.md")

    with pytest.raises(ValueError, match="supported_asset_names"):
        template.render(
            json_schema="{}",
            raw_title="demo",
            raw_text="demo text",
            source="Reuters",
            source_type="mainstream_media",
            publish_time="2026-06-19T00:00:00Z",
            supported_event_types="ai_export_control, unknown",
        )

