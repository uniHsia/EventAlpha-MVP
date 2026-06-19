"""Calibration service for LLM novelty scores."""

from __future__ import annotations

from dataclasses import dataclass, field


HIGH_IMPACT_EVENT_TYPES = {
    "ai_export_control",
    "geopolitical_conflict",
    "rate_policy",
    "trade_tariff",
}


@dataclass
class NoveltyCalibrationResult:
    """Calibrated novelty score and diagnostic warnings."""

    novelty_score: float
    warnings: list[str] = field(default_factory=list)


class NoveltyCalibrationService:
    """Keep LLM novelty scores from suppressing important events too much."""

    def calibrate_novelty(
        self,
        llm_novelty: float,
        rule_based_novelty: float,
        event_type: str,
        credibility_score: float,
        raw_text: str,
    ) -> NoveltyCalibrationResult:
        """Return a calibrated novelty score."""
        warnings: list[str] = []
        llm_value = self._clamp(llm_novelty)
        rule_value = self._clamp(rule_based_novelty)

        if abs(llm_value - rule_value) > 0.25:
            warnings.append(
                f"novelty difference exceeds threshold: llm={llm_value}, rule_based={rule_value}"
            )

        final = max(llm_value, round(rule_value * 0.9, 4))
        if event_type in HIGH_IMPACT_EVENT_TYPES and final < 0.6:
            warnings.append(f"novelty floor applied for high-impact event_type={event_type}")
            final = 0.6

        if final != llm_value:
            warnings.append(f"novelty calibrated: {llm_value} -> {final}")

        return NoveltyCalibrationResult(novelty_score=round(self._clamp(final), 4), warnings=warnings)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, round(float(value), 4)))

