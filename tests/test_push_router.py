"""Tests for local subscription push routing."""

from __future__ import annotations

from eventalpha.notification import Subscriber, build_push_message, match_event_to_subscribers


def test_push_router_matches_keyword_asset_and_priority() -> None:
    event_card = {
        "事件ID": "EVT_1",
        "标题": "AI芯片出口管制升级",
        "一句话摘要": "国产AI芯片关注度上升",
        "事件等级": "A",
        "可能影响资产": ["国产AI芯片"],
    }
    subscriber = Subscriber(
        subscriber_id="demo_user_001",
        channel="wechat_placeholder",
        keywords=["出口管制"],
        assets=["国产AI芯片"],
        min_priority="A",
    )

    matches = match_event_to_subscribers(event_card, [subscriber])
    message = build_push_message(event_card, matches[0][0], reason=matches[0][1])

    assert matches
    assert message.channel == "wechat_placeholder"
    assert message.status == "pending"
    assert "出口管制" in message.reason


def test_push_router_skips_below_priority() -> None:
    event_card = {"标题": "Low event", "事件等级": "C", "一句话摘要": "AI芯片"}
    subscriber = Subscriber(subscriber_id="demo_user_001", keywords=["AI芯片"], min_priority="A")

    assert match_event_to_subscribers(event_card, [subscriber]) == []
