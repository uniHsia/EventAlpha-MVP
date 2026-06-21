"""Scheduler infrastructure for EventAlpha."""

from .apscheduler_runner import EventAlphaAPScheduler
from .job_registry import JOB_RUNNERS, get_job_runner, run_registered_job
from .jobs import (
    run_candidate_analysis,
    run_news_lifecycle_scan,
    run_scheduler_status,
    tracked_event_to_raw_news,
)
from .schemas import SchedulerJobConfig, SchedulerRunRecord
from .state_store import (
    DEFAULT_SCHEDULER_RUNS_PATH,
    DEFAULT_SCHEDULER_STATE_PATH,
    SchedulerStateStore,
)

__all__ = [
    "DEFAULT_SCHEDULER_RUNS_PATH",
    "DEFAULT_SCHEDULER_STATE_PATH",
    "EventAlphaAPScheduler",
    "JOB_RUNNERS",
    "SchedulerJobConfig",
    "SchedulerRunRecord",
    "SchedulerStateStore",
    "get_job_runner",
    "run_candidate_analysis",
    "run_news_lifecycle_scan",
    "run_registered_job",
    "run_scheduler_status",
    "tracked_event_to_raw_news",
]
