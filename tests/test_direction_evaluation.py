"""Direction evaluation rule tests."""

from __future__ import annotations

from eventalpha.agents import evaluate_direction


def test_up_direction_evaluation() -> None:
    result = evaluate_direction("up", 0.03, 0.01, 0.02)

    assert result.is_directional_call is True
    assert result.direction_correct is True
    assert result.outperformed_benchmark is True


def test_down_direction_evaluation() -> None:
    result = evaluate_direction("down", -0.03, 0.01, -0.04)

    assert result.is_directional_call is True
    assert result.direction_correct is True
    assert result.outperformed_benchmark is True
    assert result.relative_weaker_than_benchmark is True


def test_mixed_and_watch_are_not_directional_calls() -> None:
    mixed = evaluate_direction("mixed", 0.04, 0.01, 0.03)
    watch = evaluate_direction("watch", -0.02, 0.01, -0.03)

    assert mixed.is_directional_call is False
    assert mixed.direction_correct is None
    assert watch.is_directional_call is False
    assert watch.direction_correct is None


def test_neutral_direction_evaluation() -> None:
    result = evaluate_direction("neutral", 0.002, 0.001, 0.001)

    assert result.is_directional_call is True
    assert result.direction_correct is True
    assert result.outperformed_benchmark is False
