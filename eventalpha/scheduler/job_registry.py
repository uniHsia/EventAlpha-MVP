"""Registry for supported scheduler jobs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .jobs import run_candidate_analysis, run_news_lifecycle_scan, run_scheduler_status
from .schemas import SchedulerJobConfig, SchedulerRunRecord
from .state_store import SchedulerStateStore


SchedulerJobRunner = Callable[[SchedulerJobConfig, SchedulerStateStore], SchedulerRunRecord]

JOB_RUNNERS: dict[str, SchedulerJobRunner] = {
    "news_lifecycle_scan": run_news_lifecycle_scan,
    "candidate_analysis": run_candidate_analysis,
    "scheduler_status": run_scheduler_status,
}


def get_job_runner(job_type: str) -> SchedulerJobRunner:
    """Return the runner for a supported scheduler job type."""
    if job_type not in JOB_RUNNERS:
        raise ValueError(f"Unsupported scheduler job type: {job_type}")
    return JOB_RUNNERS[job_type]


def run_registered_job(
    config: SchedulerJobConfig,
    store: SchedulerStateStore,
    **kwargs: Any,
) -> SchedulerRunRecord:
    """Run a job through the registry."""
    runner = get_job_runner(config.job_type)
    return runner(config, store, **kwargs)
