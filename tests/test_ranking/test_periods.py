"""
PeriodType 和时间范围计算测试。
不依赖任何外部服务。
"""
from datetime import timezone

import pytest

from app.ranking.periods import PERIOD_TOP_N, PeriodType, get_period_dates, get_period_range
from app.utils.time_utils import (
    get_last_month_range,
    get_last_week_range,
    get_yesterday_range,
)


def test_period_top_n_values():
    assert PERIOD_TOP_N[PeriodType.DAILY] == 10
    assert PERIOD_TOP_N[PeriodType.WEEKLY] == 10
    assert PERIOD_TOP_N[PeriodType.MONTHLY] == 20


def test_get_period_range_daily():
    start, end = get_period_range(PeriodType.DAILY)
    assert start < end
    assert start.tzinfo is not None
    # 昨日：end - start ≈ 24h
    diff = end - start
    assert 86300 <= diff.total_seconds() <= 86400


def test_get_period_range_weekly():
    start, end = get_period_range(PeriodType.WEEKLY)
    assert start < end
    diff = end - start
    # 一周约 7 天
    assert 6 * 86400 <= diff.total_seconds() <= 7 * 86400


def test_get_period_range_monthly():
    start, end = get_period_range(PeriodType.MONTHLY)
    assert start < end
    # 上月天数在 28-31 天之间
    diff_days = (end - start).days
    assert 27 <= diff_days <= 31


def test_get_period_dates_returns_date_type():
    from datetime import date
    start, end = get_period_dates(PeriodType.DAILY)
    assert isinstance(start, date)
    assert isinstance(end, date)
    # 日榜 start == end（同一天），周/月榜 start < end
    assert start <= end


def test_get_period_range_start_before_end_all_types():
    for period_type in PeriodType:
        start, end = get_period_range(period_type)
        assert start < end, f"{period_type} 的 start 应早于 end"


def test_yesterday_range_midnight_aligned():
    start, end = get_yesterday_range()
    assert start.hour == 0
    assert start.minute == 0
    assert start.second == 0


def test_last_week_range_monday_to_sunday():
    from datetime import timedelta
    start, end = get_last_week_range()
    # start 是周一
    assert start.weekday() == 0
    # end 是周日
    assert end.weekday() == 6


def test_period_type_values():
    assert PeriodType.DAILY.value == "daily"
    assert PeriodType.WEEKLY.value == "weekly"
    assert PeriodType.MONTHLY.value == "monthly"
