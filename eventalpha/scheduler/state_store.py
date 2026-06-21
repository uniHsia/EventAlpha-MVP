"""JSON-backed state and run-log store for scheduler jobs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import SchedulerJobConfig, SchedulerRunRecord
from .tracking_policy import TrackingPolicy


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
        raw = self._load_state()
        jobs = raw.get("jobs", []) if isinstance(raw, dict) else []
        return [SchedulerJobConfig.model_validate(job) for job in jobs]

    def save_config(self, jobs: list[SchedulerJobConfig]) -> None:
        """Save scheduler job config as readable JSON."""
        payload = self._load_state()
        payload["jobs"] = [job.model_dump(mode="json") for job in jobs]
        self._write_state(payload)

    def load_tracking_policies(self) -> list[TrackingPolicy]:
        """Load saved urgent-mode tracking policies."""
        raw = self._load_state()
        policies = raw.get("tracking_policies", []) if isinstance(raw, dict) else []
        return [TrackingPolicy.model_validate(policy) for policy in policies]

    def save_tracking_policies(self, policies: list[TrackingPolicy]) -> None:
        """Save urgent-mode tracking policies while preserving job config."""
        payload = self._load_state()
        payload["tracking_policies"] = [policy.model_dump(mode="json") for policy in policies]
        self._write_state(payload)

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
            try:
                records.append(SchedulerRunRecord.model_validate(json.loads(line)))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return list(reversed(records))[: max(limit, 0)]

    def get_last_successful_run(self, job_id: str) -> SchedulerRunRecord | None:
        """Return the latest successful run for one job."""
        for record in self.list_recent_runs(limit=10_000):
            if record.job_id == job_id and record.status == "success":
                return record
        return None

    def _load_state(self) -> dict[str, Any]:
        """Load raw state JSON, returning an empty payload when missing."""
        if not self.state_path.exists():
            return {}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return raw if isinstance(raw, dict) else {}

    def _write_state(self, payload: dict[str, Any]) -> None:
        """Write raw scheduler state JSON."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
