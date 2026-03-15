"""
榜单周期定义。

PeriodType 枚举 + 各周期的时间范围计算。
所有时间均为 UTC，与快照采集保持一致。

业务语义（已锁定）：
  日榜：昨日 00:00:00 → 昨日 23:59:59
  周榜：上周一 00:00:00 → 上周日 23:59:59
  月榜：上月第一天 00:00:00 → 上月最后一天 23:59:59
  三种榜单排序依据均为「周期内播放量增量」
"""
from datetime import date, datetime
from enum import Enum

from app.utils.time_utils import (
    get_last_month_range,
    get_last_week_range,
    get_yesterday_range,
)


class PeriodType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# 各周期对应的 Top N
PERIOD_TOP_N: dict[PeriodType, int] = {
    PeriodType.DAILY: 10,
    PeriodType.WEEKLY: 10,
    PeriodType.MONTHLY: 20,
}


def get_period_range(period_type: PeriodType) -> tuple[datetime, datetime]:
    """返回指定周期的 (start, end) UTC 时间范围。"""
    if period_type == PeriodType.DAILY:
        return get_yesterday_range()
    if period_type == PeriodType.WEEKLY:
        return get_last_week_range()
    if period_type == PeriodType.MONTHLY:
        return get_last_month_range()
    raise ValueError(f"未知 PeriodType: {period_type}")


def get_period_dates(period_type: PeriodType) -> tuple[date, date]:
    """返回 (period_start, period_end) 的 date 类型，用于写入 DB。"""
    start, end = get_period_range(period_type)
    return start.date(), end.date()
