"""Write local full-demo summary reports."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from eventalpha.schemas.base import RISK_DISCLAIMER


def write_demo_summary(
    summary: Any,
    *,
    reports_dir: str | Path,
    summary_date: date | None = None,
) -> dict[str, Path]:
    """Write Markdown and JSON full-demo summary files."""
    target_date = summary_date or date.today()
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = target_date.strftime("%Y%m%d")
    md_path = output_dir / f"full_demo_summary_{stamp}.md"
    json_path = output_dir / f"full_demo_summary_{stamp}.json"
    payload = _to_jsonable(summary)
    md_path.write_text(render_demo_summary_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"markdown": md_path, "json": json_path}


def render_demo_summary_markdown(summary: dict[str, Any]) -> str:
    """Render a compact Chinese Markdown summary for the full demo."""
    steps = summary.get("steps", [])
    prediction = summary.get("prediction", {})
    streamlit_instruction = summary.get("streamlit_instruction") or (
        "streamlit run app_streamlit.py -- --demo-mode"
    )
    lines = [
        f"# EventAlpha Full Demo Summary - {summary.get('demo_date', '')}",
        "",
        "> 本内容仅用于事件研究和市场分析，不构成投资建议。",
        "",
        f"- Demo scenario: {summary.get('scenario_id', 'unknown')}",
        f"- Prediction: {prediction.get('prediction_id', 'n/a')}",
        f"- EventCard: {summary.get('event_card', {}).get('card_id', 'n/a')}",
        f"- ReviewResults: {summary.get('review_result_count', 0)}",
        f"- RuleUpdates: {summary.get('rule_update_count', 0)}",
        f"- Daily Briefing: {summary.get('briefing_paths', {}).get('markdown', 'n/a')}",
        "",
        "## Steps",
    ]
    for index, step in enumerate(steps, start=1):
        counts = ", ".join(f"{key}={value}" for key, value in step.get("counts", {}).items())
        lines.append(f"{index}. {step.get('step_name')}: {step.get('status')}")
        if counts:
            lines.append(f"   - {counts}")
        for path in step.get("output_paths", []):
            lines.append(f"   - {path}")
        for warning in step.get("warnings", [])[:3]:
            lines.append(f"   - warning: {warning}")
    lines.extend(
        [
            "",
            "## Next",
            "",
            f"```bash\n{streamlit_instruction}\n```",
            "",
            summary.get("risk_disclaimer") or RISK_DISCLAIMER,
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _to_jsonable(summary: Any) -> dict[str, Any]:
    if hasattr(summary, "model_dump"):
        return summary.model_dump(mode="json")
    if isinstance(summary, dict):
        return summary
    raise TypeError("summary must be a Pydantic model or dict")
