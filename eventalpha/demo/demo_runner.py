"""End-to-end offline demo runner."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from pydantic import Field

from eventalpha.demo.demo_report import write_demo_summary
from eventalpha.demo.demo_scenarios import DemoScenario, get_demo_scenario
from eventalpha.demo.demo_state import (
    DemoStatePaths,
    default_demo_paths,
    default_state_paths,
    prepare_demo_state,
)
from eventalpha.news import EventLifecycleStore
from eventalpha.news.lifecycle import EventTimelineEntry, TrackedEvent
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas.base import EventAlphaModel, RISK_DISCLAIMER, utc_now
from eventalpha.services import LedgerService
from eventalpha.ui import StreamlitDataLoader
from scripts.run_daily_briefing import build_daily_briefing
from scripts.run_scheduler import run_scheduler_once


STREAMLIT_DEMO_INSTRUCTION = "streamlit run app_streamlit.py -- --demo-mode"


class DemoStepResult(EventAlphaModel):
    """One step in the full demo run."""

    step_name: str
    status: str = "success"
    counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class FullDemoSummary(EventAlphaModel):
    """Structured result of the offline end-to-end demo."""

    scenario_id: str
    demo_date: date
    isolated_state: bool = True
    paths: dict[str, str] = Field(default_factory=dict)
    steps: list[DemoStepResult] = Field(default_factory=list)
    prediction: dict[str, Any] = Field(default_factory=dict)
    event_card: dict[str, Any] = Field(default_factory=dict)
    due_review_task: dict[str, Any] = Field(default_factory=dict)
    review_result_count: int = 0
    rule_update_count: int = 0
    briefing_paths: dict[str, str] = Field(default_factory=dict)
    streamlit_data_check: dict[str, int] = Field(default_factory=dict)
    demo_summary_paths: dict[str, str] = Field(default_factory=dict)
    streamlit_instruction: str = STREAMLIT_DEMO_INSTRUCTION
    risk_disclaimer: str = RISK_DISCLAIMER


class FullDemoRunner:
    """Run a deterministic local EventAlpha demo chain."""

    def __init__(
        self,
        *,
        scenario_id: str = "ai_export_control",
        paths: DemoStatePaths | None = None,
        use_default_state: bool = False,
        reset_state: bool = False,
        write_summary: bool = False,
        project_root: str | Path | None = None,
    ) -> None:
        self.scenario = get_demo_scenario(scenario_id)
        self.paths = paths or (
            default_state_paths(project_root) if use_default_state else default_demo_paths(project_root)
        )
        self.reset_state = reset_state
        self.write_summary = write_summary
        self.summary = FullDemoSummary(
            scenario_id=self.scenario.scenario_id,
            demo_date=date.today(),
            isolated_state=self.paths.isolated,
            paths=_paths_payload(self.paths),
        )

    def run(self) -> FullDemoSummary:
        """Execute the full demo flow."""
        result = self._prepare_state()
        self.summary.steps.append(result)
        pipeline = self._run_event_pipeline()
        self.summary.steps.append(pipeline["step"])
        due = self._make_due_review_task(pipeline["prediction_id"], self.scenario.review_horizon)
        self.summary.steps.append(due)
        auto_review = self._run_auto_review()
        self.summary.steps.append(auto_review)
        urgent_scan = self._run_urgent_event_scan()
        self.summary.steps.append(urgent_scan)
        briefing = self._generate_daily_briefing()
        self.summary.steps.append(briefing)
        streamlit_check = self._validate_streamlit_data()
        self.summary.steps.append(streamlit_check)
        if self.write_summary:
            summary_step = self._write_summary_report()
            self.summary.steps.append(summary_step)
        return self.summary

    def _prepare_state(self) -> DemoStepResult:
        prepare_demo_state(self.paths, reset=self.reset_state)
        return DemoStepResult(
            step_name="prepare_demo_state",
            counts={"reset": int(self.reset_state), "isolated_state": int(self.paths.isolated)},
            output_paths=[
                str(self.paths.data_root),
                str(self.paths.reports_dir),
                str(self.paths.ledger_path),
            ],
            notes=list(self.paths.notes),
        )

    def _run_event_pipeline(self) -> dict[str, Any]:
        ledger = LedgerService(self.paths.ledger_path)
        result = run_event_pipeline(self.scenario.raw_news, ledger_service=ledger)
        prediction = result["prediction_ledger_entry"]
        event_card = result["event_card"]
        review_tasks = list(result.get("review_tasks") or [])
        self._seed_lifecycle(result)
        self.summary.prediction = {
            "prediction_id": prediction.prediction_id,
            "event_id": prediction.event_id,
            "event_title": prediction.event_title,
            "event_type": prediction.event_type,
            "predicted_assets": [asset.asset_name for asset in prediction.predicted_assets],
        }
        self.summary.event_card = {
            "card_id": event_card.card_id,
            "event_id": event_card.event_id,
            "event_title": event_card.event_title,
            "event_level": event_card.event_level,
        }
        return {
            "prediction_id": prediction.prediction_id,
            "step": DemoStepResult(
                step_name="run_demo_event_pipeline",
                counts={
                    "predictions": 1,
                    "event_cards": 1,
                    "review_tasks": len(review_tasks),
                    "predicted_assets": len(prediction.predicted_assets),
                },
                output_paths=[str(self.paths.ledger_path), str(self.paths.lifecycle_store_path)],
                notes=["Rule-based offline event pipeline completed."],
            ),
        }

    def _make_due_review_task(self, prediction_id: str, horizon: str) -> DemoStepResult:
        ledger = LedgerService(self.paths.ledger_path)
        tasks = ledger.get_review_tasks(prediction_id)
        if not tasks:
            raise RuntimeError(f"No review tasks found for prediction {prediction_id}.")
        target = next((task for task in tasks if task.horizon == horizon), tasks[0])
        due_at = utc_now() - timedelta(minutes=1)
        with ledger.repo.connect() as conn:
            conn.execute(
                "UPDATE review_tasks SET due_at = ?, status = 'pending' WHERE task_id = ?",
                (due_at.isoformat(), target.task_id),
            )
            conn.commit()
        self.summary.due_review_task = {
            "task_id": target.task_id,
            "prediction_id": prediction_id,
            "horizon": target.horizon,
            "due_at": due_at.isoformat(),
        }
        return DemoStepResult(
            step_name="make_due_review_task",
            counts={"due_review_tasks": 1},
            notes=[f"Marked {target.horizon} task as due for the demo."],
        )

    def _run_auto_review(self) -> DemoStepResult:
        result = run_scheduler_once(
            "auto_review_runner",
            execute=True,
            market_provider="mock",
            ledger_path=self.paths.ledger_path,
            state_path=self.paths.scheduler_state_path,
            runs_path=self.paths.scheduler_runs_path,
            max_review_tasks=5,
            review_horizons=[self.scenario.review_horizon],
        )
        record = result["record"]
        review_count = _note_int(record.notes, "ReviewResult count")
        rule_count = _note_int(record.notes, "RuleUpdate count")
        self.summary.review_result_count = review_count
        self.summary.rule_update_count = rule_count
        if record.status not in {"success", "dry_run"}:
            raise RuntimeError(f"auto_review_runner failed: {'; '.join(record.errors)}")
        return DemoStepResult(
            step_name="run_auto_review_runner",
            status=record.status,
            counts={
                "due_tasks": record.candidate_items,
                "reviewed_tasks": record.analyzed_events,
                "review_results": review_count,
                "rule_updates": rule_count,
            },
            warnings=list(record.warnings),
            errors=list(record.errors),
            output_paths=[str(self.paths.ledger_path), str(self.paths.scheduler_runs_path)],
            notes=list(record.notes),
        )

    def _run_urgent_event_scan(self) -> DemoStepResult:
        result = run_scheduler_once(
            "urgent_event_scan",
            execute=True,
            state_path=self.paths.scheduler_state_path,
            runs_path=self.paths.scheduler_runs_path,
            lifecycle_store_path=self.paths.lifecycle_store_path,
            limit=5,
        )
        record = result["record"]
        if record.status != "success":
            raise RuntimeError(f"urgent_event_scan failed: {'; '.join(record.errors)}")
        return DemoStepResult(
            step_name="run_urgent_event_scan",
            status=record.status,
            counts={
                "active_events": record.candidate_items,
                "tracking_policies": record.lifecycle_updates,
            },
            warnings=list(record.warnings),
            errors=list(record.errors),
            output_paths=[str(self.paths.scheduler_state_path), str(self.paths.scheduler_runs_path)],
            notes=list(record.notes),
        )

    def _generate_daily_briefing(self) -> DemoStepResult:
        result = build_daily_briefing(
            briefing_date=self.summary.demo_date,
            max_items=10,
            write_report=True,
            reports_dir=self.paths.reports_dir,
            state_path=self.paths.scheduler_state_path,
            runs_path=self.paths.scheduler_runs_path,
            ledger_path=self.paths.ledger_path,
            lifecycle_store_path=self.paths.lifecycle_store_path,
        )
        paths = result.get("paths") or {}
        self.summary.briefing_paths = {key: str(value) for key, value in paths.items()}
        return DemoStepResult(
            step_name="generate_daily_briefing",
            counts={"sections": len(result["briefing"].sections)},
            output_paths=[str(value) for value in paths.values()],
            warnings=list(result["briefing"].warnings),
            notes=["Daily briefing Markdown and JSON generated under the demo reports directory."],
        )

    def _validate_streamlit_data(self) -> DemoStepResult:
        loader = StreamlitDataLoader(
            reports_dir=self.paths.reports_dir,
            lifecycle_store_path=self.paths.lifecycle_store_path,
            state_path=self.paths.scheduler_state_path,
            runs_path=self.paths.scheduler_runs_path,
            ledger_path=self.paths.ledger_path,
            max_items=50,
        )
        bundle = loader.load(briefing_date=self.summary.demo_date)
        data = bundle["collected_data"]
        counts = {
            "event_cards": len(data.event_cards),
            "review_results": len(data.review_results),
            "rule_updates": len(data.rule_updates),
            "active_events": len(data.active_events),
            "briefing_reports": len(bundle.get("reports") or []),
        }
        self.summary.streamlit_data_check = counts
        missing = [
            label
            for label, count in counts.items()
            if label in {"event_cards", "review_results", "rule_updates", "briefing_reports"} and count <= 0
        ]
        if missing:
            raise RuntimeError(f"Streamlit data check failed; missing: {', '.join(missing)}")
        return DemoStepResult(
            step_name="validate_streamlit_data",
            counts=counts,
            warnings=list(bundle.get("warnings") or []),
            notes=["StreamlitDataLoader can read demo reports, scheduler state, lifecycle state, and ledger rows."],
        )

    def _write_summary_report(self) -> DemoStepResult:
        paths = write_demo_summary(self.summary, reports_dir=self.paths.reports_dir, summary_date=self.summary.demo_date)
        self.summary.demo_summary_paths = {key: str(value) for key, value in paths.items()}
        return DemoStepResult(
            step_name="write_demo_summary",
            counts={"summary_files": len(paths)},
            output_paths=[str(value) for value in paths.values()],
        )

    def _seed_lifecycle(self, pipeline_result: dict[str, Any]) -> None:
        event = pipeline_result["structured_event"]
        card = pipeline_result["event_card"]
        now = utc_now()
        tracked = TrackedEvent(
            canonical_title=event.event_title,
            current_summary=event.summary or card.one_sentence,
            lifecycle_stage="developing",
            first_seen_at=now,
            last_seen_at=now,
            source_count=2,
            sources=["Reuters", "Mock Global News"],
            credibility_status="multi_source_supported",
            official_evidence_status="official_source_present",
            latest_claims=[
                "official_source_present",
                "matched_existing",
                "deterministic mock/demo scenario",
            ],
            dominant_keywords=[
                "ai_export_control",
                "AI chip",
                "export control",
                "semiconductor",
                "event_level=A",
            ],
            timeline=[
                EventTimelineEntry(
                    timestamp=now,
                    update_type="new_event",
                    title=event.event_title,
                    summary=event.summary or card.one_sentence,
                    source_count=2,
                    credibility_status="multi_source_supported",
                    official_evidence_status="official_source_present",
                    notes=[
                        "lifecycle_stage=developing",
                        "official_source_present",
                        "matched_existing",
                        "event_level=A",
                        "demo/mock data only",
                    ],
                )
            ],
        )
        store = EventLifecycleStore(self.paths.lifecycle_store_path).load()
        store.upsert(tracked)
        store.save()


def run_full_demo(
    *,
    scenario_id: str = "ai_export_control",
    reset_state: bool = False,
    write_summary: bool = False,
    use_default_state: bool = False,
    paths: DemoStatePaths | None = None,
    project_root: str | Path | None = None,
) -> FullDemoSummary:
    """Convenience wrapper for the full demo runner."""
    return FullDemoRunner(
        scenario_id=scenario_id,
        paths=paths,
        use_default_state=use_default_state,
        reset_state=reset_state,
        write_summary=write_summary,
        project_root=project_root,
    ).run()


def _paths_payload(paths: DemoStatePaths) -> dict[str, str]:
    return {
        "data_root": str(paths.data_root),
        "reports_dir": str(paths.reports_dir),
        "ledger_path": str(paths.ledger_path),
        "scheduler_state_path": str(paths.scheduler_state_path),
        "scheduler_runs_path": str(paths.scheduler_runs_path),
        "lifecycle_store_path": str(paths.lifecycle_store_path),
    }


def _note_int(notes: list[str], label: str) -> int:
    prefix = f"{label}:"
    for note in notes:
        if note.startswith(prefix):
            try:
                return int(note.removeprefix(prefix).strip().rstrip("."))
            except ValueError:
                return 0
    return 0
