"""Tests for urgent-mode tracking policies."""

from __future__ import annotations

from eventalpha.scheduler import EventUrgencyScore, TrackingPolicyService


def test_tracking_policy_service_maps_urgent_to_15_minutes() -> None:
    """Urgent events should get the shortest supported interval."""
    policy = TrackingPolicyService().build_policy(_score("urgent", 80))

    assert policy.tracking_mode == "urgent"
    assert policy.scan_interval_minutes == 15
    assert policy.analyze is True


def test_tracking_policy_service_maps_high_to_enhanced() -> None:
    """High-priority events should get enhanced tracking."""
    policy = TrackingPolicyService().build_policy(_score("high", 60))

    assert policy.tracking_mode == "enhanced"
    assert policy.scan_interval_minutes == 30
    assert policy.analyze is True


def test_tracking_policy_service_maps_normal_to_60_minutes() -> None:
    """Normal events should remain analyzable at hourly cadence."""
    policy = TrackingPolicyService().build_policy(_score("normal", 35))

    assert policy.tracking_mode == "normal"
    assert policy.scan_interval_minutes == 60
    assert policy.analyze is True


def test_tracking_policy_service_maps_background_to_no_analysis() -> None:
    """Background events should be scanned slowly and not analyzed by default."""
    policy = TrackingPolicyService().build_policy(_score("background", 20))

    assert policy.tracking_mode == "background"
    assert policy.scan_interval_minutes == 240
    assert policy.analyze is False


def test_tracking_policy_service_maps_ignore_to_paused() -> None:
    """Ignored events should be paused."""
    policy = TrackingPolicyService().build_policy(_score("ignore", 0))

    assert policy.tracking_mode == "paused"
    assert policy.scan_interval_minutes == 0
    assert policy.analyze is False


def _score(level: str, value: float) -> EventUrgencyScore:
    return EventUrgencyScore(
        tracked_event_id=f"TRACK_{level}",
        title=f"{level} event",
        urgency_score=value,
        urgency_level=level,
    )
