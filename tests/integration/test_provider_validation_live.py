"""Optional live provider validation integration test."""

from __future__ import annotations

import os

import pytest

from scripts.validate_provider_routes import build_validation_report


@pytest.mark.skipif(
    os.getenv("EVENTALPHA_RUN_LIVE_PROVIDER_VALIDATION") != "1",
    reason="Set EVENTALPHA_RUN_LIVE_PROVIDER_VALIDATION=1 to run live provider validation.",
)
def test_live_provider_validation_has_results() -> None:
    """Run live AkShare route validation only when explicitly enabled."""
    report = build_validation_report(event_type="rate_policy", refresh_cache=True, trust_env=False)

    assert report["summary"]["total_routes"] >= 1
