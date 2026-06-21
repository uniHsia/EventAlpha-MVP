"""Tests for EventCard deduplication in daily briefings."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingCollectedData, DailyBriefingBuilder


def test_event_card_dedup_keeps_latest_and_counts_duplicates() -> None:
    """Repeated cards for one event should collapse to the latest row."""
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        event_cards=[
            {
                "id": 1,
                "card_id": "CARD_OLD",
                "event_id": "EVT_1",
                "event_title": "US upgrades AI chip export controls",
                "event_type": "ai_export_control",
                "event_level": "A",
                "one_sentence": "AI controls may affect semiconductors.",
                "created_at": "2026-06-20T00:00:00+00:00",
            },
            {
                "id": 2,
                "card_id": "CARD_NEW",
                "event_id": "EVT_1",
                "event_title": "US upgrades AI chip export controls",
                "event_type": "ai_export_control",
                "event_level": "A",
                "one_sentence": "AI controls may affect semiconductors.",
                "created_at": "2026-06-21T00:00:00+00:00",
            },
        ],
    )

    section = _section(DailyBriefingBuilder(max_items=10).build(data), "event_cards")

    assert len(section.items) == 1
    assert section.items[0].item_id == "CARD_NEW"
    assert section.items[0].metadata["duplicate_count"] == 2
    assert any("duplicate_count=2" in detail for detail in section.items[0].details)
    assert any("duplicates collapsed: 1" in note for note in section.notes)


def test_event_card_dedup_collapses_same_content_with_different_event_ids() -> None:
    """Same title/type/summary should collapse even if event ids differ."""
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        event_cards=[
            {
                "id": 1,
                "card_id": "CARD_1",
                "event_id": "EVT_1",
                "event_title": "US upgrades AI chip export controls",
                "event_type": "ai_export_control",
                "one_sentence": "AI controls may affect semiconductors.",
            },
            {
                "id": 2,
                "card_id": "CARD_2",
                "event_id": "EVT_2",
                "event_title": "US upgrades AI chip export controls",
                "event_type": "ai_export_control",
                "one_sentence": "AI controls may affect semiconductors.",
            },
        ],
    )

    section = _section(DailyBriefingBuilder(max_items=10).build(data), "event_cards")

    assert len(section.items) == 1
    assert section.items[0].metadata["duplicate_count"] == 2


def test_event_card_dedup_collapses_same_title_type_with_different_summary() -> None:
    """Same title/type should collapse even when card wording changed."""
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        event_cards=[
            {
                "id": 1,
                "card_id": "CARD_1",
                "event_id": "EVT_1",
                "event_title": "US upgrades AI chip export controls",
                "event_type": "ai_export_control",
                "one_sentence": "Earlier wording.",
            },
            {
                "id": 2,
                "card_id": "CARD_2",
                "event_id": "EVT_2",
                "event_title": "US upgrades AI chip export controls",
                "event_type": "ai_export_control",
                "one_sentence": "Later wording with more details.",
            },
        ],
    )

    section = _section(DailyBriefingBuilder(max_items=10).build(data), "event_cards")

    assert len(section.items) == 1
    assert section.items[0].item_id == "CARD_2"
    assert section.items[0].summary == "Later wording with more details."


def _section(briefing, section_id):
    return next(section for section in briefing.sections if section.section_id == section_id)
