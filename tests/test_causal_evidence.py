"""Tests for causal evidence summaries."""

from __future__ import annotations

from eventalpha.reasoning import build_causal_evidence_summary


def test_causal_evidence_uses_source_historical_and_missing() -> None:
    summary = build_causal_evidence_summary(
        {
            "事件ID": "EVT_1",
            "标题": "AI芯片出口管制升级",
            "因果链摘要": ["出口管制升级", "海外 GPU 供应受限", "国产 AI 芯片受关注"],
            "信息来源": ["Mock Global News"],
            "可能影响资产": ["国产AI芯片"],
            "后续验证指标": ["政策细则"],
        },
        historical_cases=[
            {
                "案例名称": "历史出口管制案例",
                "事件类型": "ai_export_control",
                "摘要": "出口管制影响 GPU 供应链",
                "source_label": "Demo Historical Case",
            }
        ],
        ledger_rows=[{"事件": "AI芯片出口管制升级", "资产": "国产AI芯片", "source_label": "Prediction Ledger"}],
    )

    evidence_types = [item.evidence_type for item in summary.items]

    assert "source" in evidence_types
    assert "historical_case" in evidence_types or "market_data" in evidence_types
    assert all(item.verification_indicator or not item.verification_needed for item in summary.items)


def test_causal_evidence_marks_missing_without_chain_data() -> None:
    summary = build_causal_evidence_summary({"标题": "Unknown event"})

    assert summary.items
    assert summary.items[0].evidence_type in {"missing", "assumption"}
    assert summary.items[0].verification_needed is True
