"""Tests for prompt template loading and rendering."""

from __future__ import annotations

import pytest

from eventalpha.llm import PromptTemplate


def test_prompt_template_reads_and_renders(tmp_path) -> None:
    """PromptTemplate should load files and substitute variables."""
    path = tmp_path / "prompt.md"
    path.write_text("Hello {name}", encoding="utf-8")

    rendered = PromptTemplate.from_file(path).render(name="EventAlpha")

    assert rendered == "Hello EventAlpha"


def test_prompt_template_missing_variable_raises() -> None:
    """Missing variables should raise a clear ValueError."""
    template = PromptTemplate("Hello {name}")

    with pytest.raises(ValueError, match="Missing prompt template variable"):
        template.render()


def test_bundled_extraction_prompt_loads() -> None:
    """The bundled extraction prompt should be available."""
    template = PromptTemplate.from_file("eventalpha/prompts/extraction_event.md")

    rendered = template.render(json_schema="{}", raw_news_json="{}")

    assert "StructuredEvent" in rendered

