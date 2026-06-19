"""Optional LLM-backed causal reasoning agent."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, get_args

import yaml

from eventalpha.config import PROJECT_ROOT
from eventalpha.llm import PromptTemplate, StructuredRunner, pydantic_to_json_schema
from eventalpha.llm.errors import LLMOutputValidationError
from eventalpha.schemas import (
    CausalChain,
    Direction,
    EventVerification,
    ImpactScore,
    StructuredEvent,
)
from eventalpha.schemas.base import new_id, utc_now
from eventalpha.services import AssetNormalizationService, IndustryNormalizationService

from .causal_reasoning import RuleBasedCausalReasoningAgent


FailureMode = Literal["strict", "fallback"]


class LLMCausalReasoningAgent:
    """Build CausalChain objects with structured LLM output and guardrails."""

    def __init__(
        self,
        runner: StructuredRunner,
        prompt_path: str | Path = "eventalpha/prompts/causal_reasoning.md",
        fallback_agent=None,
        failure_mode: FailureMode = "strict",
        asset_normalizer: AssetNormalizationService | None = None,
        industry_normalizer: IndustryNormalizationService | None = None,
    ) -> None:
        if failure_mode not in {"strict", "fallback"}:
            raise ValueError("failure_mode must be 'strict' or 'fallback'")
        self.runner = runner
        self.prompt_path = prompt_path
        self.fallback_agent = fallback_agent or RuleBasedCausalReasoningAgent()
        self.failure_mode = failure_mode
        self.asset_normalizer = asset_normalizer or AssetNormalizationService()
        self.industry_normalizer = industry_normalizer or IndustryNormalizationService()
        self.warnings: list[str] = []

    def build_chain(
        self,
        structured_event: StructuredEvent,
        verification: EventVerification | None = None,
        impact_score: ImpactScore | None = None,
        supported_assets: list[str] | None = None,
        extraction_warnings: list[str] | None = None,
    ) -> CausalChain:
        """Build and post-process an LLM causal chain."""
        self.warnings = []
        try:
            chain = self.runner.run(
                prompt=self._render_prompt(
                    structured_event=structured_event,
                    verification=verification,
                    impact_score=impact_score,
                    supported_assets=supported_assets,
                    extraction_warnings=extraction_warnings,
                ),
                output_schema=CausalChain,
                system_prompt=(
                    "You are an EventAlpha causal reasoning component. "
                    "Return only schema-valid JSON and no investment advice."
                ),
                prompt_name="causal_reasoning",
            )
            return self._post_process(
                chain=chain,
                structured_event=structured_event,
                verification=verification,
                impact_score=impact_score,
                supported_assets=supported_assets,
                extraction_warnings=extraction_warnings,
            )
        except Exception as exc:
            if self.failure_mode == "strict":
                raise
            warning = f"LLM causal reasoning failed; fell back to rule-based causal chain: {exc}"
            self.warnings.append(warning)
            return self.fallback_agent.build_chain(
                structured_event=structured_event,
                verification=verification,
                impact_score=impact_score,
                supported_assets=supported_assets,
                extraction_warnings=extraction_warnings,
            )

    def _post_process(
        self,
        chain: CausalChain,
        structured_event: StructuredEvent,
        verification: EventVerification | None,
        impact_score: ImpactScore | None,
        supported_assets: list[str] | None,
        extraction_warnings: list[str] | None,
    ) -> CausalChain:
        allowlist = self._supported_assets(structured_event, supported_assets)
        normalized_assets = self.asset_normalizer.normalize_asset_list(chain.affected_assets)
        self.warnings.extend(self.asset_normalizer.warnings)

        filtered_assets: list[str] = []
        filtered_keys: set[str] = set()
        rejected_assets: list[str] = []
        for asset in normalized_assets:
            key = self._norm(asset)
            if key in allowlist:
                if key not in filtered_keys:
                    filtered_assets.append(asset)
                    filtered_keys.add(key)
            else:
                rejected_assets.append(asset)

        if rejected_assets:
            self.warnings.append(
                "Filtered unsupported causal affected_assets: " + ", ".join(rejected_assets)
            )

        if not filtered_assets:
            fallback_assets = [
                asset
                for asset in self.asset_normalizer.normalize_asset_list(
                    structured_event.affected_assets_hint
                )
                if self._norm(asset) in allowlist
            ]
            if fallback_assets:
                filtered_assets = _dedupe(fallback_assets)
                self.warnings.append(
                    "Used StructuredEvent.affected_assets_hint because LLM causal assets were unsupported"
                )
            elif self.failure_mode == "fallback":
                self.warnings.append(
                    "LLM causal chain had no supported assets; fell back to rule-based causal chain"
                )
                return self.fallback_agent.build_chain(
                    structured_event=structured_event,
                    verification=verification,
                    impact_score=impact_score,
                    supported_assets=supported_assets,
                    extraction_warnings=extraction_warnings,
                )
            else:
                raise LLMOutputValidationError(
                    "LLM causal chain did not contain any supported affected_assets"
                )

        confidence = self._guard_confidence(
            confidence=chain.confidence,
            structured_event=structured_event,
            verification=verification,
            extraction_warnings=extraction_warnings or [],
        )
        direction = chain.direction
        if direction not in get_args(Direction):
            self.warnings.append(f"Invalid causal direction replaced with mixed: {direction}")
            direction = "mixed"

        if len(chain.logic) > 6:
            self.warnings.append(f"Causal chain is long: {len(chain.logic)} steps")

        return chain.model_copy(
            update={
                "chain_id": new_id("CHAIN"),
                "event_id": structured_event.event_id,
                "created_at": utc_now(),
                "affected_assets": filtered_assets,
                "direction": direction,
                "confidence": confidence,
            }
        )

    def _guard_confidence(
        self,
        confidence: float,
        structured_event: StructuredEvent,
        verification: EventVerification | None,
        extraction_warnings: list[str],
    ) -> float:
        guarded = max(0.0, min(1.0, float(confidence)))
        low_verification = verification and verification.verification_status in {
            "needs_confirmation",
            "low_confidence",
            "rumor",
        }
        if structured_event.status == "rumor" or low_verification:
            capped = min(guarded, 0.55)
            if capped != guarded:
                self.warnings.append("Reduced causal confidence for rumor or low-verification event")
            guarded = capped
        if len(extraction_warnings) >= 3:
            capped = min(guarded, 0.65)
            if capped != guarded:
                self.warnings.append("Reduced causal confidence due to extraction warnings")
            guarded = capped
        return round(guarded, 4)

    def _render_prompt(
        self,
        structured_event: StructuredEvent,
        verification: EventVerification | None,
        impact_score: ImpactScore | None,
        supported_assets: list[str] | None,
        extraction_warnings: list[str] | None,
    ) -> str:
        template = PromptTemplate.from_file(self.prompt_path)
        event_payload = structured_event.model_dump(mode="json")
        return template.render(
            json_schema=json.dumps(pydantic_to_json_schema(CausalChain), ensure_ascii=False),
            event_json=json.dumps(event_payload, ensure_ascii=False, indent=2),
            structured_event_json=json.dumps(event_payload, ensure_ascii=False, indent=2),
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
            supported_assets=", ".join(self._supported_asset_names(structured_event, supported_assets)),
            supported_industries=", ".join(self.industry_normalizer.standard_names),
            extraction_warnings=json.dumps(extraction_warnings or [], ensure_ascii=False),
        )

    def _supported_assets(
        self,
        structured_event: StructuredEvent,
        supported_assets: list[str] | None,
    ) -> set[str]:
        return {
            self._norm(asset)
            for asset in self._supported_asset_names(structured_event, supported_assets)
        }

    def _supported_asset_names(
        self,
        structured_event: StructuredEvent,
        supported_assets: list[str] | None,
    ) -> list[str]:
        names: list[str] = []
        names.extend(supported_assets or [])
        names.extend(structured_event.affected_assets_hint)
        names.extend(self.asset_normalizer.standard_names)
        names.extend(_asset_mapping_seed_names())
        return _dedupe(names)

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"\s+", "", str(value)).casefold()


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


def _asset_mapping_seed_names() -> list[str]:
    path = PROJECT_ROOT / "eventalpha" / "rules" / "asset_mapping_seed.yaml"
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    names: list[str] = []
    if isinstance(payload, dict):
        for config in payload.values():
            if isinstance(config, dict):
                for asset in config.get("assets", []) or []:
                    if isinstance(asset, dict) and asset.get("asset_name"):
                        names.append(str(asset["asset_name"]))
    return names
