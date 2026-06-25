"""Review-result feedback signals for future prediction calibration."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel, utc_now


class RuleFeedbackSignal(EventAlphaModel):
    """A lightweight signal derived from ReviewResult or RuleUpdate history."""

    rule_key: str
    event_type: str
    asset: str | None = None
    adjustment: float
    reason: str
    evidence_count: int
    source: str
    needs_verification: bool = False


def load_rule_feedback_signals(
    *,
    review_results: list[dict[str, Any]] | None = None,
    rule_updates: list[dict[str, Any]] | None = None,
    ledger_rows: list[dict[str, Any]] | None = None,
) -> list[RuleFeedbackSignal]:
    """Build feedback signals from local review and rule update rows."""
    reviews = review_results or []
    updates = rule_updates or []
    ledger_by_prediction = {
        str(row.get("PredictionID") or row.get("prediction_id") or ""): row
        for row in ledger_rows or []
    }
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in reviews:
        prediction_id = str(row.get("PredictionID") or row.get("prediction_id") or "")
        ledger = ledger_by_prediction.get(prediction_id, {})
        event_type = str(row.get("事件类型") or ledger.get("事件类型") or ledger.get("event_type") or "unknown")
        asset = str(row.get("资产") or row.get("asset_name") or ledger.get("资产") or ledger.get("asset_name") or "未记录")
        grouped[(event_type, asset)].append(row)

    signals: list[RuleFeedbackSignal] = []
    for (event_type, asset), rows in grouped.items():
        positives = sum(1 for row in rows if _is_positive_review(row))
        negatives = sum(1 for row in rows if _is_negative_review(row))
        unknowns = max(len(rows) - positives - negatives, 0)
        adjustment = min(0.03 * positives, 0.10) if positives >= negatives else -min(0.05 * negatives, 0.10)
        if positives == negatives:
            adjustment = 0.0
        signals.append(
            RuleFeedbackSignal(
                rule_key=f"{event_type}:{asset}",
                event_type=event_type,
                asset=None if asset == "未记录" else asset,
                adjustment=round(_clamp(adjustment), 4),
                reason=f"ReviewResult positive={positives}, negative={negatives}, unknown={unknowns}.",
                evidence_count=len(rows),
                source="review_result",
                needs_verification=unknowns > 0 or negatives > 0,
            )
        )

    for row in updates:
        rule_id = str(row.get("RuleID") or row.get("rule_id") or "rule_update")
        action = str(row.get("动作") or row.get("update_action") or "").casefold()
        adjustment = 0.03 if "strengthen" in action else -0.05 if "weaken" in action else 0.0
        signals.append(
            RuleFeedbackSignal(
                rule_key=rule_id,
                event_type=_event_type_from_rule(rule_id),
                asset=None,
                adjustment=round(_clamp(adjustment), 4),
                reason=str(row.get("理由") or row.get("reason") or "RuleUpdate generated after review."),
                evidence_count=int(row.get("次数") or row.get("count") or 1),
                source="rule_update",
                needs_verification=adjustment <= 0,
            )
        )
    return signals


def apply_rule_feedback_to_prediction(
    prediction_or_asset: dict[str, Any],
    signals: list[RuleFeedbackSignal],
) -> dict[str, Any]:
    """Return a copy with feedback adjustment metadata; do not mutate ledger rows."""
    row = dict(prediction_or_asset)
    event_type = str(row.get("事件类型") or row.get("event_type") or "unknown")
    asset = str(row.get("资产") or row.get("asset_name") or "")
    relevant = [
        signal
        for signal in signals
        if signal.event_type in {event_type, "unknown"} and (not signal.asset or not asset or signal.asset == asset)
    ]
    total = round(_clamp(sum(signal.adjustment for signal in relevant)), 4)
    base = _confidence(row)
    adjusted = None if base is None else round(max(0.0, min(1.0, base + total)), 4)
    row["feedback_adjustment"] = total
    row["feedback_adjusted_confidence"] = adjusted
    row["feedback_reasons"] = [signal.reason for signal in relevant[:5]]
    row["needs_verification"] = any(signal.needs_verification for signal in relevant)
    return row


def write_rule_feedback_report(
    signals: list[RuleFeedbackSignal],
    *,
    reports_dir: str | Path = "reports",
    report_date: date | None = None,
    demo_mode: bool = False,
) -> dict[str, str]:
    """Write rule feedback signals to JSON and Markdown."""
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    stamp = (report_date or date.today()).strftime("%Y%m%d")
    json_path = reports_path / f"rule_feedback_signals_{stamp}.json"
    md_path = reports_path / f"rule_feedback_signals_{stamp}.md"
    payload = {
        "generated_at": utc_now().isoformat(),
        "demo_mode": demo_mode,
        "signal_count": len(signals),
        "signals": [signal.model_dump(mode="json") for signal in signals],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_rule_feedback_markdown(signals, demo_mode=demo_mode), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def render_rule_feedback_markdown(signals: list[RuleFeedbackSignal], *, demo_mode: bool = False) -> str:
    """Render feedback signals as Markdown."""
    lines = [
        "# EventAlpha 复盘反馈信号",
        "",
        f"- generated_at: {utc_now().isoformat()}",
        f"- demo_mode: {str(demo_mode).lower()}",
        f"- signal_count: {len(signals)}",
        "",
        "| Rule Key | Event Type | Asset | Adjustment | Evidence | Source | Needs Verification | Reason |",
        "|---|---|---|---:|---:|---|---|---|",
    ]
    for signal in signals:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(signal.rule_key),
                    _md(signal.event_type),
                    _md(signal.asset or "--"),
                    f"{signal.adjustment:+.2f}",
                    str(signal.evidence_count),
                    _md(signal.source),
                    "yes" if signal.needs_verification else "no",
                    _md(signal.reason),
                ]
            )
            + " |"
        )
    return "\n".join(lines).strip() + "\n"


def _is_positive_review(row: dict[str, Any]) -> bool:
    return row.get("因果有效性") == "valid" or row.get("causal_validity") == "valid" or row.get("方向正确") == "是" or row.get("direction_correct") in {True, 1}


def _is_negative_review(row: dict[str, Any]) -> bool:
    return row.get("因果有效性") == "invalid" or row.get("causal_validity") == "invalid" or row.get("方向正确") == "否" or row.get("direction_correct") in {False, 0}


def _event_type_from_rule(rule_id: str) -> str:
    text = rule_id.casefold()
    if "ai" in text or "export" in text:
        return "ai_export_control"
    if "geo" in text or "conflict" in text:
        return "geopolitical_conflict"
    if "rate" in text:
        return "rate_policy"
    return "unknown"


def _confidence(row: dict[str, Any]) -> float | None:
    for key in ("最终置信度", "final_confidence", "confidence"):
        value = row.get(key)
        if value in {None, "", "未记录", "--"}:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _clamp(value: float) -> float:
    return max(-0.10, min(0.10, float(value)))


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
