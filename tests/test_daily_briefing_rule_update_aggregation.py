"""Tests for RuleUpdate aggregation in daily briefings."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingCollectedData, DailyBriefingBuilder


def test_rule_update_aggregation_counts_and_keeps_latest_weights() -> None:
    """Rule updates should group by rule id and action."""
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        rule_updates=[
            {
                "id": 1,
                "update_id": "UPD_OLD",
                "rule_id": "RULE_AI_EXPORT_001",
                "update_action": "slightly_strengthen",
                "old_weight": 0.7,
                "new_weight": 0.72,
                "reason": "old reason",
                "created_at": "2026-06-20T00:00:00+00:00",
            },
            {
                "id": 2,
                "update_id": "UPD_NEW",
                "rule_id": "RULE_AI_EXPORT_001",
                "update_action": "slightly_strengthen",
                "old_weight": 0.72,
                "new_weight": 0.74,
                "reason": "latest reason",
                "created_at": "2026-06-21T00:00:00+00:00",
            },
        ],
    )

    section = _section(DailyBriefingBuilder(max_items=10).build(data), "rule_updates")

    assert len(section.items) == 1
    assert section.items[0].title == "RULE_AI_EXPORT_001 slightly_strengthen ×2"
    assert section.items[0].summary == "latest reason"
    assert section.items[0].metadata["count"] == 2
    assert "new_weight=0.74" in section.items[0].details


def _section(briefing, section_id):
    return next(section for section in briefing.sections if section.section_id == section_id)
