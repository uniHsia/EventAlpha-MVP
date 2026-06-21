"""JSON-backed state and run-log store for scheduler jobs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import SchedulerJobConfig, SchedulerRunRecord


DEFAULT_SCHEDULER_STATE_PATH = Path("data/scheduler_state.json")
DEFAULT_SCHEDULER_RUNS_PATH = Path("data/scheduler_runs.jsonl")


class SchedulerStateStore:
    """Persist scheduler config and run records in readable local files."""

    def __init__(
        self,
        state_path: str | Path = DEFAULT_SCHEDULER_STATE_PATH,
        runs_path: str | Path = DEFAULT_SCHEDULER_RUNS_PATH,
    ) -> None:
        self.state_path = Path(state_path)
        self.runs_path = Path(runs_path)

    def load_config(self) -> list[SchedulerJobConfig]:
        """Load scheduler job config, returning an empty list when missing."""
        if not self.state_path.exists():
            return []
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        jobs = raw.get("jobs", []) if isinstance(raw, dict) else []
        return [SchedulerJobConfig.model_validate(job) for job in jobs]

    def save_config(self, jobs: list[SchedulerJobConfig]) -> None:
        """Save scheduler job config as readable JSON."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "jobs": [job.model_dump(mode="json") for job in jobs],
        }
        self.state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def append_run(self, record: SchedulerRunRecord) -> None:
        """Append one run record to the JSONL run log."""
        self.runs_path.parent.mkdir(parents=True, exist_ok=True)
        with self.runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False))
            handle.write("\n")

    def list_recent_runs(self, limit: int = 20) -> list[SchedulerRunRecord]:
        """Return recent run records newest first."""
        if not self.runs_path.exists():
            return []
        records = []
        for line in self.runs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            records.append(SchedulerRunRecord.model_validate(json.loads(line)))
        return list(reversed(records))[: max(limit, 0)]

    def get_last_successful_run(self, job_id: str) -> SchedulerRunRecord | None:
        """Return the latest successful run for one job."""
        for record in self.list_recent_runs(limit=10_000):
            if record.job_id == job_id and record.status == "success":
                return record
        return None
