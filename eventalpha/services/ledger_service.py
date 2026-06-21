"""SQLite-backed Prediction Ledger service."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

from eventalpha.config import get_db_path, get_rules_dir
from eventalpha.repositories import SQLiteRepository
from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    EventCard,
    EventVerification,
    ImpactScore,
    MarketMapping,
    PredictedAsset,
    PredictionLedgerEntry,
    PredictionReviewSummary,
    RawNews,
    ReviewResult,
    ReviewTask,
    RuleUpdate,
    StructuredEvent,
)
from eventalpha.schemas.base import utc_now


def _json(value: Any) -> str:
    """Serialize a value as UTF-8 JSON text."""
    return json.dumps(value, ensure_ascii=False, default=str)


def _loads(value: str | None, default: Any) -> Any:
    """Load JSON text with a fallback value."""
    if not value:
        return default
    return json.loads(value)


def _iso(value: Any) -> str | None:
    """Return ISO text for datetime-like values."""
    return value.isoformat() if hasattr(value, "isoformat") else value


class LedgerService:
    """Persist MVP pipeline artifacts in SQLite."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else get_db_path()
        self.repo = SQLiteRepository(self.db_path)
        self.initialize_db()

    def initialize_db(self) -> None:
        """Initialize the SQLite schema and seed causal rules."""
        self.repo.initialize()
        self._seed_causal_rules()

    def _seed_causal_rules(self) -> None:
        rules_file = get_rules_dir() / "causal_rules_seed.yaml"
        if not rules_file.exists():
            return
        data = yaml.safe_load(rules_file.read_text(encoding="utf-8")) or {}
        with self.repo.connect() as conn:
            for rule in data.get("rules", []):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO causal_rules
                    (rule_id, event_type, rule, weight, success_rate, review_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rule["rule_id"],
                        rule.get("event_type"),
                        rule.get("rule"),
                        rule.get("weight", 0.5),
                        rule.get("success_rate", 0.0),
                        rule.get("review_count", 0),
                    ),
                )
            conn.commit()

    def save_raw_news(self, raw_news: RawNews) -> str:
        """Save raw news input."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_news
                (raw_id, title, source, source_type, publish_time, url, language,
                 raw_text, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_news.raw_id,
                    raw_news.title,
                    raw_news.source,
                    raw_news.source_type,
                    _iso(raw_news.publish_time),
                    raw_news.url,
                    raw_news.language,
                    raw_news.raw_text,
                    _json(raw_news.metadata),
                    _iso(raw_news.created_at),
                ),
            )
            conn.commit()
        return raw_news.raw_id

    def save_event(self, event: StructuredEvent) -> str:
        """Save a structured event."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO events
                (event_id, raw_id, event_type, event_title, summary, entities_json,
                 locations_json, event_time, status, affected_industries_json,
                 affected_assets_hint_json, novelty_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.raw_id,
                    event.event_type,
                    event.event_title,
                    event.summary,
                    _json(event.entities),
                    _json(event.locations),
                    _iso(event.event_time) if event.event_time else None,
                    event.status,
                    _json(event.affected_industries),
                    _json(event.affected_assets_hint),
                    event.novelty_score,
                    _iso(event.created_at),
                ),
            )
            conn.commit()
        return event.event_id

    def save_verification(self, verification: EventVerification) -> str:
        """Save event verification."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO event_verifications
                (verification_id, event_id, credibility_score, verification_status,
                 source_classification, content_contains_official_claim,
                 evidence_json, risk_flags_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verification.verification_id,
                    verification.event_id,
                    verification.credibility_score,
                    verification.verification_status,
                    verification.source_classification,
                    int(verification.content_contains_official_claim),
                    _json(verification.evidence),
                    _json(verification.risk_flags),
                    _iso(verification.created_at),
                ),
            )
            conn.commit()
        return verification.verification_id

    def save_score(self, score: ImpactScore) -> str:
        """Save impact score."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO event_scores
                (score_id, event_id, impact_score, event_level, trigger_alert,
                 tracking_mode, score_breakdown_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.score_id,
                    score.event_id,
                    score.impact_score,
                    score.event_level,
                    int(score.trigger_alert),
                    score.tracking_mode,
                    _json(score.score_breakdown),
                    _iso(score.created_at),
                ),
            )
            conn.commit()
        return score.score_id

    def save_causal_chain(self, chain: CausalChain) -> str:
        """Save causal chain."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO causal_chains
                (chain_id, event_id, logic_json, affected_assets_json, direction,
                 time_horizon, confidence, rationale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chain.chain_id,
                    chain.event_id,
                    _json([step.model_dump(mode="json") for step in chain.logic]),
                    _json(chain.affected_assets),
                    chain.direction,
                    chain.time_horizon,
                    chain.confidence,
                    chain.rationale,
                    _iso(chain.created_at),
                ),
            )
            conn.commit()
        return chain.chain_id

    def save_anti_spurious_check(self, check: AntiSpuriousCheck) -> str:
        """Save anti-spurious check."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO anti_spurious_checks
                (check_id, event_id, chain_id, spurious_risk, issues_json,
                 required_verifications_json, adjusted_confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check.check_id,
                    check.event_id,
                    check.chain_id,
                    check.spurious_risk,
                    _json(check.issues),
                    _json(check.required_verifications),
                    check.adjusted_confidence,
                    _iso(check.created_at),
                ),
            )
            conn.commit()
        return check.check_id

    def save_market_mapping(self, mapping: MarketMapping) -> str:
        """Save market mapping."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO market_mappings
                (mapping_id, event_id, mapped_assets_json, watch_indicators_json,
                 mapping_notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    mapping.mapping_id,
                    mapping.event_id,
                    _json([asset.model_dump(mode="json") for asset in mapping.mapped_assets]),
                    _json(mapping.watch_indicators),
                    mapping.mapping_notes,
                    _iso(mapping.created_at),
                ),
            )
            conn.commit()
        return mapping.mapping_id

    def save_event_card(self, card: EventCard) -> str:
        """Save event card."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO event_cards
                (card_id, event_id, event_title, event_level, credibility_score,
                 one_sentence, what_happened, sources_json, causal_chain_summary_json,
                 possible_impacts_json, risk_factors_json, verification_indicators_json,
                 risk_disclaimer, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.card_id,
                    card.event_id,
                    card.event_title,
                    card.event_level,
                    card.credibility_score,
                    card.one_sentence,
                    card.what_happened,
                    _json(card.sources),
                    _json(card.causal_chain_summary),
                    _json(card.possible_impacts),
                    _json(card.risk_factors),
                    _json(card.verification_indicators),
                    card.risk_disclaimer,
                    _iso(card.created_at),
                ),
            )
            conn.commit()
        return card.card_id

    def save_prediction_ledger(self, entry: PredictionLedgerEntry) -> str:
        """Save prediction ledger entry and predicted assets."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO prediction_ledger
                (prediction_id, event_id, event_title, event_type, publish_time,
                 event_level, credibility_score, impact_score, causal_chain_ids_json,
                 risk_flags_json, review_schedule_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.prediction_id,
                    entry.event_id,
                    entry.event_title,
                    entry.event_type,
                    _iso(entry.publish_time),
                    entry.event_level,
                    entry.credibility_score,
                    entry.impact_score,
                    _json(entry.causal_chain_ids),
                    _json(entry.risk_flags),
                    _json(entry.review_schedule),
                    entry.status,
                    _iso(entry.created_at),
                ),
            )
            conn.execute("DELETE FROM predicted_assets WHERE prediction_id = ?", (entry.prediction_id,))
            for asset in entry.predicted_assets:
                conn.execute(
                    """
                    INSERT INTO predicted_assets
                    (prediction_id, asset_name, asset_type, direction, time_window,
                     asset_confidence, chain_confidence, anti_spurious_adjusted_confidence,
                     final_confidence, confidence, benchmark, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.prediction_id,
                        asset.asset_name,
                        asset.asset_type,
                        asset.direction,
                        asset.time_window,
                        asset.asset_confidence,
                        asset.chain_confidence,
                        asset.anti_spurious_adjusted_confidence,
                        asset.final_confidence,
                        asset.confidence,
                        asset.benchmark,
                        _iso(asset.created_at),
                    ),
                )
            conn.commit()
        return entry.prediction_id

    def create_review_tasks(self, entry: PredictionLedgerEntry) -> list[ReviewTask]:
        """Create and persist T+1/T+3/T+7 review tasks."""
        day_map = {"T+1": 1, "T+3": 3, "T+7": 7}
        now = utc_now()
        tasks = [
            ReviewTask(
                prediction_id=entry.prediction_id,
                event_id=entry.event_id,
                horizon=horizon,
                due_at=now + timedelta(days=day_map[horizon]),
            )
            for horizon in entry.review_schedule
        ]
        with self.repo.connect() as conn:
            for task in tasks:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO review_tasks
                    (task_id, prediction_id, event_id, horizon, due_at, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.task_id,
                        task.prediction_id,
                        task.event_id,
                        task.horizon,
                        _iso(task.due_at),
                        task.status,
                        _iso(task.created_at),
                    ),
                )
            conn.commit()
        return tasks

    def get_prediction(self, prediction_id: str) -> PredictionLedgerEntry | None:
        """Read one prediction ledger entry."""
        with self.repo.connect() as conn:
            row = conn.execute(
                "SELECT * FROM prediction_ledger WHERE prediction_id = ?",
                (prediction_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_prediction(conn, row)

    def get_latest_prediction(self) -> PredictionLedgerEntry | None:
        """Read the most recent prediction ledger entry."""
        with self.repo.connect() as conn:
            row = conn.execute(
                "SELECT * FROM prediction_ledger ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            return self._row_to_prediction(conn, row)

    def _row_to_prediction(self, conn, row) -> PredictionLedgerEntry:
        assets_rows = conn.execute(
            "SELECT * FROM predicted_assets WHERE prediction_id = ? ORDER BY id",
            (row["prediction_id"],),
        ).fetchall()
        assets = [self._row_to_predicted_asset(asset) for asset in assets_rows]
        return PredictionLedgerEntry(
            prediction_id=row["prediction_id"],
            event_id=row["event_id"],
            event_title=row["event_title"],
            event_type=row["event_type"],
            publish_time=row["publish_time"],
            event_level=row["event_level"],
            credibility_score=row["credibility_score"],
            impact_score=row["impact_score"],
            causal_chain_ids=_loads(row["causal_chain_ids_json"], []),
            predicted_assets=assets,
            risk_flags=_loads(row["risk_flags_json"], []),
            review_schedule=_loads(row["review_schedule_json"], ["T+1", "T+3", "T+7"]),
            status=row["status"],
            created_at=row["created_at"],
        )

    def _row_to_predicted_asset(self, row) -> PredictedAsset:
        asset_confidence = row["asset_confidence"]
        if asset_confidence is None:
            asset_confidence = row["confidence"] if row["confidence"] is not None else 0.5
        chain_confidence = row["chain_confidence"] if row["chain_confidence"] is not None else 0.5
        adjusted = (
            row["anti_spurious_adjusted_confidence"]
            if row["anti_spurious_adjusted_confidence"] is not None
            else chain_confidence
        )
        final_confidence = (
            row["final_confidence"]
            if row["final_confidence"] is not None
            else row["confidence"]
            if row["confidence"] is not None
            else round(asset_confidence * adjusted, 4)
        )
        return PredictedAsset(
            asset_name=row["asset_name"],
            asset_type=row["asset_type"],
            direction=row["direction"],
            time_window=row["time_window"],
            asset_confidence=asset_confidence,
            chain_confidence=chain_confidence,
            anti_spurious_adjusted_confidence=adjusted,
            final_confidence=final_confidence,
            confidence=row["confidence"] if row["confidence"] is not None else final_confidence,
            benchmark=row["benchmark"],
            created_at=row["created_at"],
        )

    def get_review_tasks(self, prediction_id: str) -> list[ReviewTask]:
        """Read persisted review tasks for a prediction."""
        with self.repo.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM review_tasks WHERE prediction_id = ? ORDER BY id",
                (prediction_id,),
            ).fetchall()
            return [
                ReviewTask(
                    task_id=row["task_id"],
                    prediction_id=row["prediction_id"],
                    event_id=row["event_id"],
                    horizon=row["horizon"],
                    due_at=row["due_at"],
                    status=row["status"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def list_due_review_tasks(
        self,
        now: Any | None = None,
        limit: int = 5,
        horizons: list[str] | None = None,
    ) -> list[ReviewTask]:
        """Read pending review tasks due at or before the supplied timestamp."""
        due_at = _iso(now or utc_now())
        params: list[Any] = [due_at]
        horizon_clause = ""
        if horizons:
            placeholders = ", ".join("?" for _ in horizons)
            horizon_clause = f" AND horizon IN ({placeholders})"
            params.extend(horizons)
        params.append(max(int(limit), 1))
        with self.repo.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM review_tasks
                WHERE status = 'pending'
                  AND due_at <= ?
                  {horizon_clause}
                ORDER BY due_at ASC, id ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [
                ReviewTask(
                    task_id=row["task_id"],
                    prediction_id=row["prediction_id"],
                    event_id=row["event_id"],
                    horizon=row["horizon"],
                    due_at=row["due_at"],
                    status=row["status"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def update_review_task_status(self, task_id: str, status: str) -> None:
        """Update an existing review task status without changing schema."""
        with self.repo.connect() as conn:
            conn.execute(
                "UPDATE review_tasks SET status = ? WHERE task_id = ?",
                (status, task_id),
            )
            conn.commit()

    def save_review_result(self, result: ReviewResult) -> str:
        """Save a single-asset review result."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO review_results
                (review_id, prediction_id, event_id, horizon, asset_name,
                 predicted_direction, benchmark, actual_return, benchmark_return,
                 excess_return, is_directional_call, direction_correct,
                 outperformed_benchmark, direction_evaluation_json, asset_confidence,
                 final_confidence, causal_validity, review_conclusion, error_type,
                 risk_disclaimer, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.review_id,
                    result.prediction_id,
                    result.event_id,
                    result.horizon,
                    result.asset_name,
                    result.predicted_direction,
                    result.benchmark,
                    result.actual_return,
                    result.benchmark_return,
                    result.excess_return,
                    int(result.is_directional_call),
                    int(result.direction_correct),
                    int(result.outperformed_benchmark),
                    _json(result.direction_evaluation.model_dump(mode="json"))
                    if result.direction_evaluation
                    else None,
                    result.asset_confidence,
                    result.final_confidence,
                    result.causal_validity,
                    result.review_conclusion,
                    result.error_type,
                    result.risk_disclaimer,
                    _iso(result.created_at),
                ),
            )
            conn.commit()
        return result.review_id

    def save_review_summary(self, summary: PredictionReviewSummary) -> str:
        """Save an aggregate prediction review summary."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO prediction_review_summaries
                (summary_id, prediction_id, event_id, horizon, total_assets,
                 reviewed_assets, direction_correct_count, outperform_count,
                 valid_causal_count, invalid_causal_count, watch_or_mixed_count,
                 average_excess_return, conclusion_level, summary_text,
                 error_types_json, rule_update_suggestions_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.summary_id,
                    summary.prediction_id,
                    summary.event_id,
                    summary.horizon,
                    summary.total_assets,
                    summary.reviewed_assets,
                    summary.direction_correct_count,
                    summary.outperform_count,
                    summary.valid_causal_count,
                    summary.invalid_causal_count,
                    summary.watch_or_mixed_count,
                    summary.average_excess_return,
                    summary.conclusion_level,
                    summary.summary_text,
                    _json(summary.error_types),
                    _json(summary.rule_update_suggestions),
                    _iso(summary.created_at),
                ),
            )
            conn.commit()
        return summary.summary_id

    def save_rule_update(self, update: RuleUpdate) -> str:
        """Save a rule update and update current causal rule weight when present."""
        with self.repo.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO rule_updates
                (update_id, rule_id, prediction_id, review_id, summary_id, old_weight,
                 new_weight, reason, update_action, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    update.update_id,
                    update.rule_id,
                    update.prediction_id,
                    update.review_id,
                    update.summary_id,
                    update.old_weight,
                    update.new_weight,
                    update.reason,
                    update.update_action,
                    _iso(update.created_at),
                ),
            )
            conn.execute(
                "UPDATE causal_rules SET weight = ?, review_count = review_count + 1 WHERE rule_id = ?",
                (update.new_weight, update.rule_id),
            )
            conn.commit()
        return update.update_id

    def get_review_results(self, prediction_id: str) -> list[dict[str, Any]]:
        """Return raw review result rows for tests and demos."""
        with self.repo.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM review_results WHERE prediction_id = ? ORDER BY id",
                (prediction_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_review_summaries(self, prediction_id: str) -> list[dict[str, Any]]:
        """Return raw review summary rows for tests and demos."""
        with self.repo.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM prediction_review_summaries WHERE prediction_id = ? ORDER BY id",
                (prediction_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_rule_updates(self, prediction_id: str) -> list[dict[str, Any]]:
        """Return raw rule update rows for tests and demos."""
        with self.repo.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM rule_updates WHERE prediction_id = ? ORDER BY id",
                (prediction_id,),
            ).fetchall()
            return [dict(row) for row in rows]
