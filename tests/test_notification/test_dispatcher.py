"""
NotificationDispatcher + Formatters 测试。
"""
import pytest

from app.notification.base import NotificationChannel, RankingResult
from app.notification.dispatcher import NotificationDispatcher
from app.notification.formatters import (
    format_email_body,
    format_email_subject,
    format_feishu_card,
)


def make_result(period_type="daily", items=None) -> RankingResult:
    if items is None:
        items = [
            {"rank": 1, "video_title": "视频A", "author_name": "作者A",
             "play_increment": 500_000, "play_count_end": 2_000_000, "cover_url": None},
            {"rank": 2, "video_title": "视频B", "author_name": "作者B",
             "play_increment": 300_000, "play_count_end": 1_500_000, "cover_url": None},
        ]
    return RankingResult(
        period_type=period_type,
        platform="douyin",
        track="knowledge_course",
        track_display_name="知识传播/卖课",
        period_start="2026-03-14",
        period_end="2026-03-14",
        items=items,
    )


# ── Dispatcher 测试 ──────────────────────────────────────────────

class MockChannel(NotificationChannel):
    def __init__(self, name: str, should_fail: bool = False):
        self._name = name
        self._should_fail = should_fail
        self.received: list[RankingResult] = []

    @property
    def name(self):
        return self._name

    async def send(self, result: RankingResult) -> bool:
        if self._should_fail:
            return False
        self.received.append(result)
        return True


@pytest.mark.asyncio
async def test_dispatcher_broadcasts_to_all_channels():
    dispatcher = NotificationDispatcher()
    ch1 = MockChannel("ch1")
    ch2 = MockChannel("ch2")
    dispatcher.register(ch1)
    dispatcher.register(ch2)

    result = make_result()
    await dispatcher.dispatch(result)

    assert len(ch1.received) == 1
    assert len(ch2.received) == 1


@pytest.mark.asyncio
async def test_dispatcher_one_failure_does_not_stop_others():
    dispatcher = NotificationDispatcher()
    ch_fail = MockChannel("fail_channel", should_fail=True)
    ch_ok = MockChannel("ok_channel")
    dispatcher.register(ch_fail)
    dispatcher.register(ch_ok)

    await dispatcher.dispatch(make_result())

    # ok_channel 仍然收到通知
    assert len(ch_ok.received) == 1


@pytest.mark.asyncio
async def test_dispatcher_no_channels_no_error():
    dispatcher = NotificationDispatcher()
    await dispatcher.dispatch(make_result())  # 不应抛出异常


@pytest.mark.asyncio
async def test_dispatcher_channel_exception_does_not_propagate():
    class BrokenChannel(NotificationChannel):
        @property
        def name(self): return "broken"
        async def send(self, result): raise RuntimeError("崩了")

    dispatcher = NotificationDispatcher()
    dispatcher.register(BrokenChannel())
    ch_ok = MockChannel("ok")
    dispatcher.register(ch_ok)

    await dispatcher.dispatch(make_result())
    assert len(ch_ok.received) == 1


# ── Formatters 测试 ──────────────────────────────────────────────

def test_feishu_card_structure():
    result = make_result("daily")
    card = format_feishu_card(result)
    assert card["msg_type"] == "interactive"
    assert "card" in card
    assert "header" in card["card"]
    assert "日榜" in card["card"]["header"]["title"]["content"]


def test_feishu_card_weekly():
    card = format_feishu_card(make_result("weekly"))
    assert "周榜" in card["card"]["header"]["title"]["content"]


def test_feishu_card_monthly():
    card = format_feishu_card(make_result("monthly"))
    assert "月榜" in card["card"]["header"]["title"]["content"]


def test_email_subject_contains_period():
    result = make_result("weekly")
    subject = format_email_subject(result)
    assert "周榜" in subject
    assert "知识传播/卖课" in subject


def test_email_body_contains_all_items():
    result = make_result()
    body = format_email_body(result)
    assert "视频A" in body
    assert "视频B" in body
    assert "作者A" in body


def test_email_body_formats_large_numbers():
    result = make_result(items=[{
        "rank": 1, "video_title": "视频A", "author_name": "作者",
        "play_increment": 1_234_567, "play_count_end": 5_000_000, "cover_url": None,
    }])
    body = format_email_body(result)
    assert "123.5w" in body


def test_format_number_small():
    from app.notification.formatters import _format_number
    assert _format_number(9999) == "9999"


def test_format_number_large():
    from app.notification.formatters import _format_number
    assert _format_number(10_000) == "1.0w"
    assert _format_number(123_456) == "12.3w"
