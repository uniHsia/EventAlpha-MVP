"""Schemas for scheduler-driven automatic reviews."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel


class ReviewDueTaskView(EventAlphaModel):
    """Compact scheduler view of a due review task."""

    task_id: str
    prediction_id: str
    event_id: str
    horizon: str
    due_at: datetime
    status: str
    event_title: str | None = None
    asset_count: int = 0
    notes: list[str] = Field(default_factory=list)


class AutoReviewRunSummary(EventAlphaModel):
    """Summary counters for one automatic review run."""

    due_task_count: int = 0
    reviewed_task_count: int = 0
    skipped_task_count: int = 0
    failed_task_count: int = 0
    review_result_count: int = 0
    rule_update_count: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    due_tasks: list[ReviewDueTaskView] = Field(default_factory=list)
