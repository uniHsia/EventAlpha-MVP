"""Schemas for EventAlpha scheduler jobs and run records."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from eventalpha.schemas.base import EventAlphaModel, new_id, utc_now


SchedulerJobType = Literal["news_lifecycle_scan", "candidate_analysis", "scheduler_status"]
SchedulerRunStatus = Literal["started", "success", "failed", "skipped", "dry_run"]


class SchedulerJobConfig(EventAlphaModel):
    """Configuration for one scheduler job."""

    job_id: str
    job_type: SchedulerJobType
    enabled: bool = True
    interval_minutes: int = 60
    query: str | None = None
    source: str = "rss"
    rss_feed: str | None = None
    limit: int = 10
    real_fetch: bool = False
    use_llm_extraction: bool = False
    use_llm_causal: bool = False
    use_llm_anti_spurious: bool = False
    persist: bool = False
    dry_run: bool = True

    @field_validator("interval_minutes", "limit")
    @classmethod
    def positive_int(cls, value: int) -> int:
        """Keep interval and limit positive."""
        return max(int(value), 1)


class SchedulerRunRecord(EventAlphaModel):
    """A durable record for one scheduler job run."""

    run_id: str = Field(default_factory=lambda: new_id("SCHED_RUN"))
    job_id: str
    job_type: SchedulerJobType
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    status: SchedulerRunStatus = "started"
    fetched_items: int = 0
    candidate_items: int = 0
    clusters_processed: int = 0
    lifecycle_updates: int = 0
    analyzed_events: int = 0
    errors: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def finish(
        self,
        status: SchedulerRunStatus,
        *,
        errors: list[str] | None = None,
        notes: list[str] | None = None,
    ) -> "SchedulerRunRecord":
        """Return a finished copy of this run record."""
        return self.model_copy(
            update={
                "status": status,
                "finished_at": utc_now(),
                "errors": list(errors if errors is not None else self.errors),
                "notes": list(notes if notes is not None else self.notes),
            }
        )
