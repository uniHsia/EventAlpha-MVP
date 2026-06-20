"""Tests for cluster credibility script helper."""

from __future__ import annotations

from scripts.run_cluster_credibility import run_cluster_credibility


def test_run_cluster_credibility_mock_returns_reports_offline() -> None:
    """Default helper should run with mock providers and no network."""
    result = run_cluster_credibility(limit=10)

    assert result["fetch_result"].items
    assert result["clusters"]
    assert result["reports"]
    assert result["reports"][0].cluster_id == result["clusters"][0].cluster_id
