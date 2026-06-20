"""Tests for analogy input-context completeness diagnostics."""

from __future__ import annotations

from eventalpha.history import build_demo_current_ai_export_context, build_input_context


def test_query_only_context_completeness() -> None:
    """Query-only input should report one provided dimension and seven missing dimensions."""
    context = build_input_context(query="AI chip export control")

    assert context.provided_dimensions == ["query_keywords"]
    assert "event_type" in context.missing_dimensions
    assert "affected_assets" in context.missing_dimensions
    assert context.context_completeness_score == 0.125
    assert context.context_label == "query-only"
    assert context.low_context_warning


def test_multi_dimensional_context_completeness() -> None:
    """The combined AI export-control demo should be multi-dimensional."""
    demo_context = build_demo_current_ai_export_context()
    context = build_input_context(**demo_context)

    assert len(context.provided_dimensions) >= 5
    assert context.context_label == "multi-dimensional"
    assert context.context_completeness_score >= 0.75
    assert context.low_context_warning is None
