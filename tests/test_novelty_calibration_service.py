"""Tests for novelty calibration."""

from __future__ import annotations

from eventalpha.services.novelty_calibration_service import NoveltyCalibrationService


def test_novelty_uses_rule_based_floor_when_llm_too_low() -> None:
    """LLM novelty should not fall far below rule-based baseline."""
    service = NoveltyCalibrationService()

    result = service.calibrate_novelty(0.3, 0.8, "ai_export_control", 0.7, "出口管制")

    assert result.novelty_score == 0.72
    assert any("difference exceeds" in warning for warning in result.warnings)


def test_high_impact_novelty_floor_applies() -> None:
    """High-impact event types should have a minimum novelty floor."""
    service = NoveltyCalibrationService()

    result = service.calibrate_novelty(0.2, 0.3, "rate_policy", 0.9, "央行宣布降息")

    assert result.novelty_score == 0.6
    assert any("novelty floor" in warning for warning in result.warnings)


def test_low_impact_novelty_can_remain_low() -> None:
    """Unknown events should not receive the high-impact floor."""
    service = NoveltyCalibrationService()

    result = service.calibrate_novelty(0.2, 0.3, "unknown", 0.5, "普通新闻")

    assert result.novelty_score == 0.27

