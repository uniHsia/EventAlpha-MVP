"""Tests for ReviewResult deduplication in daily briefings."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingCollectedData, DailyBriefingBuilder
from eventalpha.scheduler import SchedulerRunRecord


def test_review_result_dedup_keeps_latest_and_notes_omitted() -> None:
    """Repeated asset/horizon results should collapse and apply display limits."""
    rows = [
        _review_row(10, "REV_OLD", "PRED_1", "AI ETF", "old"),
        _review_row(11, "REV_NEW", "PRED_1", "AI ETF", "new"),
    ]
    rows.extend(_review_row(index, f"REV_{index}", "PRED_1", f"Asset {index}", "ok") for index in range(3, 10))
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        review_results=rows,
        recent_runs=[
            SchedulerRunRecord(
                job_id="auto_review_runner",
                job_type="auto_review_runner",
                status="success",
                candidate_items=1,
                analyzed_events=1,
                notes=["Reviewed task: REV_TASK_X prediction=PRED_1 assets=7 results=7.", "ReviewResult count: 7."],
            ).finish("success")
        ],
    )

    section = _section(DailyBriefingBuilder(max_items=5).build(data), "auto_reviews")
    titles = [item.title for item in section.items]

    assert len(section.items) == 5
    assert "AI ETF / T+1" in titles
    assert next(item for item in section.items if item.title == "AI ETF / T+1").summary == "new"
    assert any("ReviewResult duplicates collapsed: 1" in note for note in section.notes)
    assert any("还有" in note and "已省略" in note for note in section.notes)


def _review_row(row_id, review_id, prediction_id, asset_name, conclusion):
    return {
        "id": row_id,
        "review_id": review_id,
        "prediction_id": prediction_id,
        "event_id": "EVT_1",
        "horizon": "T+1",
        "asset_name": asset_name,
        "direction_correct": 1,
        "excess_return": 0.01,
        "causal_validity": "valid",
        "review_conclusion": conclusion,
        "error_type": "none",
        "created_at": f"2026-06-21T00:00:{min(row_id, 59):02d}+00:00",
    }


def _section(briefing, section_id):
    return next(section for section in briefing.sections if section.section_id == section_id)
