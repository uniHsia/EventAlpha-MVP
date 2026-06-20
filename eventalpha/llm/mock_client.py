"""Deterministic offline LLM client used by tests and demos."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, TypeVar

from pydantic import BaseModel

from eventalpha.schemas import AntiSpuriousCheck, CausalChain, StructuredEvent

from .errors import LLMOutputValidationError
from .schema_utils import schema_name, validate_structured_output


T = TypeVar("T", bound=BaseModel)


class MockLLMClient:
    """Return preconfigured structured outputs without network access."""

    model = "mock-llm"
    provider_base_url = "mock://local"

    def __init__(
        self,
        responses: dict[str, dict[str, Any] | str] | None = None,
        fail_first: bool = False,
    ) -> None:
        self._uses_default_responses = responses is None
        self.responses = self.default_responses() if responses is None else responses
        self.fail_first = fail_first
        self.call_counts: dict[str, int] = {}
        self.last_raw_output: dict[str, Any] | str | None = None

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
    ) -> T:
        """Return a validated mock response for ``schema``."""
        name = schema_name(schema)
        if name not in self.responses:
            raise LLMOutputValidationError(f"No mock LLM response configured for schema: {name}")

        self.call_counts[name] = self.call_counts.get(name, 0) + 1
        if self.fail_first and self.call_counts[name] == 1:
            raw_output: dict[str, Any] | str = "{not valid json"
        elif self._uses_default_responses and name == "AntiSpuriousCheck":
            raw_output = self._default_anti_spurious_response(prompt)
        else:
            configured = self.responses[name]
            raw_output = deepcopy(configured) if isinstance(configured, dict) else configured

        self.last_raw_output = raw_output
        return validate_structured_output(raw_output, schema)

    @staticmethod
    def default_responses() -> dict[str, dict[str, Any] | str]:
        """Return default mock outputs for current Phase 3A schemas."""
        event = StructuredEvent(
            raw_id="RAW_MOCK_LLM",
            event_type="ai_export_control",
            event_title="美国宣布升级 AI 芯片出口管制",
            summary="AI 芯片出口管制升级，可能影响 GPU 供应和国产替代关注度。",
            entities=["美国", "中国", "AI 芯片", "GPU"],
            locations=["美国", "中国"],
            event_time=None,
            status="announced",
            affected_industries=["半导体", "AI 算力", "服务器"],
            affected_assets_hint=["国产 AI 芯片", "服务器", "先进封装"],
            novelty_score=0.82,
        ).model_dump(mode="json")
        chain = CausalChain(
            event_id="EVT_MOCK_LLM",
            logic=[
                {"order": 1, "description": "出口管制升级", "variable_type": "policy"},
                {"order": 2, "description": "海外 GPU 供应受限", "variable_type": "supply"},
                {"order": 3, "description": "国产替代预期上升", "variable_type": "industry"},
            ],
            affected_assets=["国产 AI 芯片", "服务器"],
            direction="up",
            time_horizon="T+3",
            confidence=0.72,
            rationale="供应约束可能强化国产替代叙事，但需要订单验证。",
        ).model_dump(mode="json")
        check = AntiSpuriousCheck(
            event_id="EVT_MOCK_LLM",
            chain_id="CHAIN_MOCK_LLM",
            spurious_risk="medium",
            issues=["产业链二阶映射需要更多证据"],
            required_verifications=["检查订单、招标和资本开支信号"],
            adjusted_confidence=0.61,
        ).model_dump(mode="json")

        # Keep datetimes JSON-safe and deterministic enough for validation.
        for payload in (event, chain, check):
            if payload.get("created_at"):
                payload["created_at"] = str(payload["created_at"])
        return {
            "StructuredEvent": event,
            "CausalChain": json.loads(json.dumps(chain, ensure_ascii=False)),
            "AntiSpuriousCheck": json.loads(json.dumps(check, ensure_ascii=False)),
        }

    @staticmethod
    def _default_anti_spurious_response(prompt: str) -> dict[str, Any]:
        """Return a slightly more case-aware offline anti-spurious critique."""
        lowered = prompt.casefold()

        if '"status": "rumor"' in lowered or '"verification_status": "rumor"' in lowered:
            check = AntiSpuriousCheck(
                event_id="EVT_MOCK_LLM",
                chain_id="CHAIN_MOCK_LLM",
                spurious_risk="medium",
                issues=["Rumor cases still need official confirmation before conviction."],
                required_verifications=["Check the official filing or regulator notice."],
                adjusted_confidence=0.52,
            )
        elif "second_order_watch" in lowered or '"event_type": "earthquake_supply_chain"' in lowered:
            check = AntiSpuriousCheck(
                event_id="EVT_MOCK_LLM",
                chain_id="CHAIN_MOCK_LLM",
                spurious_risk="medium",
                issues=["Second-order watch assets still need more evidence."],
                required_verifications=["Check orders, bidding, or capex confirmation."],
                adjusted_confidence=0.61,
            )
        elif '"event_type": "rate_policy"' in lowered:
            check = AntiSpuriousCheck(
                event_id="EVT_MOCK_LLM",
                chain_id="CHAIN_MOCK_LLM",
                spurious_risk="medium",
                issues=["The market may already have priced in part of the policy move."],
                required_verifications=["Check the yield curve, FX, and policy wording."],
                adjusted_confidence=0.58,
            )
        else:
            check = AntiSpuriousCheck(
                event_id="EVT_MOCK_LLM",
                chain_id="CHAIN_MOCK_LLM",
                spurious_risk="medium",
                issues=["Follow up with direct market confirmation data."],
                required_verifications=["Check spot price, inventory, or shipment confirmation."],
                adjusted_confidence=0.61,
            )

        payload = check.model_dump(mode="json")
        if payload.get("created_at"):
            payload["created_at"] = str(payload["created_at"])
        return json.loads(json.dumps(payload, ensure_ascii=False))
