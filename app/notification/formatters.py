"""
榜单 → 各渠道消息格式转换器。
"""
from app.notification.base import RankingResult

_PERIOD_ZH = {"daily": "日榜", "weekly": "周榜", "monthly": "月榜"}
_MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}


def format_feishu_card(result: RankingResult) -> dict:
    """生成飞书消息卡片 JSON。"""
    period_zh = _PERIOD_ZH.get(result.period_type, result.period_type)
    title = f"📊 {result.track_display_name} · {period_zh} Top{len(result.items)}"
    subtitle = f"{result.period_start} ~ {result.period_end}"

    elements = []
    for item in result.items:
        medal = _MEDAL.get(item["rank"], f"{item['rank']}.")
        increment_str = _format_number(item["play_increment"])
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**{medal} {item['video_title']}**\n"
                    f"作者：{item['author_name']}｜增量播放：**+{increment_str}**"
                ),
            },
        })
        elements.append({"tag": "hr"})

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "plain_text", "content": subtitle},
                },
                {"tag": "hr"},
                *elements,
            ],
        },
    }


def format_email_subject(result: RankingResult) -> str:
    period_zh = _PERIOD_ZH.get(result.period_type, result.period_type)
    return f"【热门视频榜单】{result.track_display_name} · {period_zh} ({result.period_start})"


def format_email_body(result: RankingResult) -> str:
    period_zh = _PERIOD_ZH.get(result.period_type, result.period_type)
    lines = [
        f"{result.track_display_name} · {period_zh} Top{len(result.items)}",
        f"统计周期：{result.period_start} ~ {result.period_end}",
        "",
        "=" * 50,
    ]
    for item in result.items:
        medal = _MEDAL.get(item["rank"], f"{item['rank']}.")
        increment_str = _format_number(item["play_increment"])
        lines += [
            f"{medal}  {item['video_title']}",
            f"    作者：{item['author_name']}",
            f"    增量播放：+{increment_str}",
            "",
        ]
    return "\n".join(lines)


def _format_number(n: int) -> str:
    """将大数字格式化为易读形式：1234567 → 123.5w。"""
    if n >= 10_000:
        return f"{n / 10_000:.1f}w"
    return str(n)
