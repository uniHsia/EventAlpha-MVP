"""Tests for status calibration."""

from __future__ import annotations

from eventalpha.services.status_calibration_service import StatusCalibrationService


def test_status_calibrates_announced() -> None:
    """Announcement keywords should calibrate unknown status to announced."""
    service = StatusCalibrationService()

    result = service.calibrate_status("unknown", "央行公告降息", "中国人民银行发布决定。")

    assert result.status == "announced"
    assert any("status calibrated" in warning for warning in result.warnings)


def test_status_calibrates_happened() -> None:
    """Happened keywords should correct announced when no announcement signal exists."""
    service = StatusCalibrationService()

    result = service.calibrate_status("announced", "日本发生地震", "当地已造成供应链扰动。")

    assert result.status == "happened"


def test_status_calibrates_rumor_and_watch_signal() -> None:
    """Rumor keywords should downgrade status and watch signals should be warnings."""
    service = StatusCalibrationService()

    result = service.calibrate_status("announced", "市场传闻央行降息", "据称官方尚未确认，市场担忧波动。")

    assert result.status == "rumor"
    assert result.signal == "watch"
    assert any("watch signal" in warning for warning in result.warnings)


def test_status_priced_in_warning() -> None:
    """Priced-in wording should be diagnostic, not a status enum."""
    service = StatusCalibrationService()

    result = service.calibrate_status("announced", "央行宣布降息", "市场反应平淡，价格已提前反映。")

    assert result.status == "announced"
    assert any("priced_in_or_expected" in warning for warning in result.warnings)

