"""Optional LLM-backed anti-spurious critic agent."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from eventalpha.llm import PromptTemplate, StructuredRunner, pydantic_to_json_schema
from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    EventVerification,
    ImpactScore,
    MarketMapping,
    SpuriousRisk,
    StructuredEvent,
)
from eventalpha.schemas.base import new_id, utc_now
from eventalpha.services import (
    AntiSpuriousCalibrationService,
    AssetNormalizationService,
    CritiqueCompressionService,
)

from .anti_spurious import RuleBasedAntiSpuriousAgent


FailureMode = Literal["strict", "fallback"]


class LLMAntiSpuriousAgent:
    """Critique a causal chain with structured LLM output and guardrails."""

    def __init__(
        self,
        runner: StructuredRunner,
        prompt_path: str | Path = "eventalpha/prompts/anti_spurious_check.md",
        fallback_agent=None,
        failure_mode: FailureMode = "strict",
        asset_normalizer: AssetNormalizationService | None = None,
    ) -> None:
        if failure_mode not in {"strict", "fallback"}:
            raise ValueError("failure_mode must be 'strict' or 'fallback'")
        self.runner = runner
        self.prompt_path = prompt_path
        self.fallback_agent = fallback_agent or RuleBasedAntiSpuriousAgent()
        self.failure_mode = failure_mode
        self.asset_normalizer = asset_normalizer or AssetNormalizationService()
        self.critique_service = CritiqueCompressionService()
        self.calibration_service = AntiSpuriousCalibrationService(
            asset_normalizer=self.asset_normalizer,
            critique_service=self.critique_service,
        )
        self.warnings: list[str] = []
        self.last_diagnostics: dict[str, int | str | bool] = self._empty_diagnostics()

    def check(
        self,
        structured_event: StructuredEvent,
        causal_chain: CausalChain,
        verification: EventVerification | None = None,
        impact_score: ImpactScore | None = None,
        market_mapping: MarketMapping | None = None,
        extraction_warnings: list[str] | None = None,
        causal_warnings: list[str] | None = None,
        supported_assets: list[str] | None = None,
    ) -> AntiSpuriousCheck:
        """Run LLM anti-spurious critique and post-process the check."""
        self.warnings = []
        self.last_diagnostics = self._empty_diagnostics()
        try:
            check = self.runner.run(
                prompt=self._render_prompt(
                    structured_event=structured_event,
                    causal_chain=causal_chain,
                    verification=verification,
                    impact_score=impact_score,
                    market_mapping=market_mapping,
                    extraction_warnings=extraction_warnings,
                    causal_warnings=causal_warnings,
                    supported_assets=supported_assets,
                ),
                output_schema=AntiSpuriousCheck,
                system_prompt=(
                    "You are an EventAlpha anti-spurious critic. "
                    "Return only schema-valid JSON and no investment advice."
                ),
                prompt_name="anti_spurious_check",
            )
            return self._post_process(
                check=check,
                structured_event=structured_event,
                causal_chain=causal_chain,
                verification=verification,
                market_mapping=market_mapping,
                extraction_warnings=extraction_warnings or [],
                causal_warnings=causal_warnings or [],
                supported_assets=supported_assets,
            )
        except Exception as exc:
            if self.failure_mode == "strict":
                raise
            warning = f"LLM anti-spurious failed; fell back to rule-based anti-spurious: {exc}"
            self.warnings.append(warning)
            fallback_check = self.fallback_agent.check(
                structured_event=structured_event,
                causal_chain=causal_chain,
                verification=verification,
                impact_score=impact_score,
                market_mapping=market_mapping,
                extraction_warnings=extraction_warnings,
                causal_warnings=causal_warnings,
                supported_assets=supported_assets,
            )
            self.last_diagnostics = {
                "raw_issue_count": len(fallback_check.issues),
                "raw_required_verification_count": len(fallback_check.required_verifications),
                "final_issue_count": len(fallback_check.issues),
                "final_required_verification_count": len(fallback_check.required_verifications),
                "raw_spurious_risk": fallback_check.spurious_risk,
                "final_spurious_risk": fallback_check.spurious_risk,
                "calibration_applied": False,
                "compression_applied": False,
                "unsupported_asset_count": 0,
                "used_fallback": True,
            }
            return fallback_check

    def _post_process(
        self,
        check: AntiSpuriousCheck,
        structured_event: StructuredEvent,
        causal_chain: CausalChain,
        verification: EventVerification | None,
        market_mapping: MarketMapping | None,
        extraction_warnings: list[str],
        causal_warnings: list[str],
        supported_assets: list[str] | None,
    ) -> AntiSpuriousCheck:
        issues = list(check.issues)
        required = list(check.required_verifications)
        risk = check.spurious_risk
        adjusted = max(0.0, min(1.0, float(check.adjusted_confidence)))

        unsupported_mentions = self._unsupported_asset_mentions(
            issues + required,
            causal_chain=causal_chain,
            supported_assets=supported_assets,
        )
        if unsupported_mentions:
            self.warnings.append(
                "LLM critique referenced unsupported assets: " + ", ".join(unsupported_mentions)
            )
            issues.append(
                "LLM critique mentioned unsupported assets that need separate mapping validation: "
                + ", ".join(unsupported_mentions)
            )
            risk = _raise_risk(risk, "medium")
            adjusted = min(adjusted, max(0.0, causal_chain.confidence - 0.1))

        if not issues and not required:
            self.warnings.append("LLM anti-spurious critique was empty")
            adjusted = min(adjusted, max(0.0, causal_chain.confidence - 0.05))

        if issues and not required:
            self.warnings.append("LLM anti-spurious critique had issues but no required verifications")
            required.append("Add concrete market, policy, or fundamental verification signals.")

        weak_verification = verification and verification.verification_status in {
            "needs_confirmation",
            "low_confidence",
            "rumor",
        }
        if structured_event.status == "rumor" or weak_verification:
            risk = _raise_risk(risk, "medium")
            capped = min(adjusted, 0.55)
            if capped != adjusted:
                self.warnings.append("Reduced adjusted_confidence for rumor or weak verification")
            adjusted = capped

        if len(extraction_warnings) + len(causal_warnings) >= 3:
            risk = _raise_risk(risk, "medium")
            capped = min(adjusted, 0.65)
            if capped != adjusted:
                self.warnings.append("Reduced adjusted_confidence due to extraction/causal warnings")
            adjusted = capped

        calibrated_input = check.model_copy(
            update={
                "spurious_risk": risk,
                "issues": issues,
                "required_verifications": required,
                "adjusted_confidence": round(adjusted, 4),
            }
        )
        calibration = self.calibration_service.calibrate_check(
            check=calibrated_input,
            structured_event=structured_event,
            verification=verification,
            causal_chain=causal_chain,
            market_mapping=market_mapping,
            extraction_warnings=extraction_warnings,
            causal_warnings=causal_warnings,
            supported_assets=supported_assets,
        )
        self.warnings.extend(calibration.warnings)

        compressed = self.critique_service.compress_anti_spurious(
            issues=issues,
            required_verifications=required,
            issue_limit=5,
            verification_limit=5,
        )
        final_check = check.model_copy(
            update={
                "check_id": new_id("SPUR"),
                "event_id": structured_event.event_id,
                "chain_id": causal_chain.chain_id,
                "created_at": utc_now(),
                "spurious_risk": calibration.spurious_risk,
                "issues": compressed.issues,
                "required_verifications": compressed.required_verifications,
                "adjusted_confidence": round(calibration.adjusted_confidence, 4),
            }
        )
        self.last_diagnostics = {
            "raw_issue_count": compressed.raw_issue_count,
            "raw_required_verification_count": compressed.raw_required_verification_count,
            "final_issue_count": len(final_check.issues),
            "final_required_verification_count": len(final_check.required_verifications),
            "raw_spurious_risk": check.spurious_risk,
            "final_spurious_risk": final_check.spurious_risk,
            "calibration_applied": calibration.calibration_applied,
            "compression_applied": (
                compressed.raw_issue_count != len(final_check.issues)
                or compressed.raw_required_verification_count
                != len(final_check.required_verifications)
            ),
            "unsupported_asset_count": len(unsupported_mentions),
            "used_fallback": False,
        }
        return final_check

    def _render_prompt(
        self,
        structured_event: StructuredEvent,
        causal_chain: CausalChain,
        verification: EventVerification | None,
        impact_score: ImpactScore | None,
        market_mapping: MarketMapping | None,
        extraction_warnings: list[str] | None,
        causal_warnings: list[str] | None,
        supported_assets: list[str] | None,
    ) -> str:
        template = PromptTemplate.from_file(self.prompt_path)
        return template.render(
            json_schema=json.dumps(
                pydantic_to_json_schema(AntiSpuriousCheck),
                ensure_ascii=False,
            ),
            event_json=json.dumps(
                structured_event.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            causal_chain_json=json.dumps(
                causal_chain.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            verification_json=json.dumps(
                verification.model_dump(mode="json") if verification else {},
                ensure_ascii=False,
                indent=2,
            ),
            impact_score_json=json.dumps(
                impact_score.model_dump(mode="json") if impact_score else {},
                ensure_ascii=False,
                indent=2,
            ),
            market_mapping_json=json.dumps(
                market_mapping.model_dump(mode="json") if market_mapping else {},
                ensure_ascii=False,
                indent=2,
            ),
            extraction_warnings=json.dumps(extraction_warnings or [], ensure_ascii=False),
            causal_warnings=json.dumps(causal_warnings or [], ensure_ascii=False),
            supported_assets=", ".join(
                _dedupe((supported_assets or []) + causal_chain.affected_assets)
            ),
        )

    def _unsupported_asset_mentions(
        self,
        texts: list[str],
        causal_chain: CausalChain,
        supported_assets: list[str] | None,
    ) -> list[str]:
        allowed = {
            self._norm(asset)
            for asset in _dedupe((supported_assets or []) + causal_chain.affected_assets)
        }
        joined = " ".join(texts)
        compact = self._norm(joined)
        mentions: list[str] = []
        for asset in self.asset_normalizer.standard_names:
            key = self._norm(asset)
            if key not in allowed and (asset in joined or key in compact):
                mentions.append(asset)
        return _dedupe(mentions)

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"\s+", "", str(value)).casefold()

    @staticmethod
    def _empty_diagnostics() -> dict[str, int | str | bool]:
        return {
            "raw_issue_count": 0,
            "raw_required_verification_count": 0,
            "final_issue_count": 0,
            "final_required_verification_count": 0,
            "raw_spurious_risk": "medium",
            "final_spurious_risk": "medium",
            "calibration_applied": False,
            "compression_applied": False,
            "unsupported_asset_count": 0,
            "used_fallback": False,
        }


def _raise_risk(current: SpuriousRisk, minimum: SpuriousRisk) -> SpuriousRisk:
    order = {"low": 0, "medium": 1, "high": 2}
    reverse = {0: "low", 1: "medium", 2: "high"}
    return reverse[max(order[current], order[minimum])]  # type: ignore[return-value]


def _dedupe(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        key = re.sub(r"\s+", "", text).casefold()
        if text and key not in seen:
            results.append(text)
            seen.add(key)
    return results
