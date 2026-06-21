"""APScheduler integration for EventAlpha scheduler jobs."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from .job_registry import run_registered_job
from .schemas import SchedulerJobConfig
from .state_store import SchedulerStateStore


class EventAlphaAPScheduler:
    """Small APScheduler wrapper using in-memory interval jobs."""

    def __init__(
        self,
        configs: list[SchedulerJobConfig],
        store: SchedulerStateStore | None = None,
        *,
        scheduler: BackgroundScheduler | None = None,
    ) -> None:
        self.configs = configs
        self.store = store or SchedulerStateStore()
        self.scheduler = scheduler or BackgroundScheduler()

    def register_jobs(self) -> None:
        """Register enabled interval jobs without starting the scheduler."""
        for config in self.configs:
            if not config.enabled:
                continue
            self.scheduler.add_job(
                run_registered_job,
                "interval",
                minutes=config.interval_minutes,
                id=config.job_id,
                args=[config, self.store],
                replace_existing=True,
            )

    def start(self) -> None:
        """Register jobs and start the scheduler."""
        self.register_jobs()
        self.scheduler.start()

    def stop(self) -> None:
        """Stop the scheduler if it is running."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def list_registered_job_ids(self) -> list[str]:
        """Return registered job ids."""
        return [job.id for job in self.scheduler.get_jobs()]
