"""Text reports for case-based causal validation."""

from __future__ import annotations

from eventalpha.schemas import RISK_DISCLAIMER

from .causal_validation import CaseBasedCausalValidation


class CaseBasedCausalValidationReportBuilder:
    """Render case-based causal validation into readable text."""

    def build_text_report(self, validation: CaseBasedCausalValidation | None) -> str:
        """Build a plain-text report."""
        if validation is None:
            return f"No case-based causal validation found.\n\n{RISK_DISCLAIMER}"
        lines = [
            "Case-Based Causal Validation Report",
            f"current_event={validation.current_event_title}",
            f"event_type={validation.event_type or 'none'}",
            f"overall_validation={validation.overall_validation}",
            f"confidence_adjustment_hint={validation.confidence_adjustment_hint:.4f}",
            "signals=",
        ]
        for signal in validation.signals:
            lines.append(
                "  "
                + (
                    f"{signal.signal_type}: strength={signal.strength}, "
                    f"reliability={signal.reliability}, "
                    f"source={signal.source_case_title or signal.source_case_id or 'none'}, "
                    f"chain_steps={_join_numbers(signal.affected_chain_steps)}, "
                    f"assets={_join(signal.related_assets)}, "
                    f"rationale={signal.rationale}"
                )
            )
            if signal.risk_notes:
                lines.append(f"    risk_notes={_join(signal.risk_notes)}")
        lines.append("asset_signals=")
        for asset_signal in validation.asset_signals:
            lines.append(
                "  "
                + (
                    f"{asset_signal.asset_name}: historical_support={asset_signal.historical_support}, "
                    f"support_score={asset_signal.support_score:.4f}, "
                    f"reliability={asset_signal.reliability}, "
                    f"supporting_cases={_join(asset_signal.supporting_cases)}, "
                    f"weakening_cases={_join(asset_signal.weakening_cases)}"
                )
            )
            if asset_signal.required_verifications:
                lines.append(f"    required_verifications={_join(asset_signal.required_verifications)}")
        lines.extend(
            [
                "transferable_lessons=" + _join(validation.transferable_lessons),
                "non_transferable_lessons=" + _join(validation.non_transferable_lessons),
                "required_verifications=" + _join(validation.required_verifications),
                "validation_notes=" + _join(validation.validation_notes),
                "risk_notes=" + _join(validation.risk_notes),
                RISK_DISCLAIMER,
            ]
        )
        return "\n".join(lines)


def _join(values: list[str]) -> str:
    return " | ".join(values) if values else "none"


def _join_numbers(values: list[int]) -> str:
    return ", ".join(str(value) for value in values) if values else "none"
