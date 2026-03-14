from datetime import date, datetime, time, timedelta, timezone


def floor_to_hour(dt: datetime) -> datetime:
    """将时间截断到整点小时，消除快照采集时间漂移。"""
    return dt.replace(minute=0, second=0, microsecond=0)


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_yesterday_range() -> tuple[datetime, datetime]:
    """昨日 00:00:00 → 23:59:59 (UTC)。"""
    today = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    yesterday_start = today - timedelta(days=1)
    yesterday_end = today - timedelta(seconds=1)
    return yesterday_start, yesterday_end


def get_last_week_range() -> tuple[datetime, datetime]:
    """上周一 00:00:00 → 上周日 23:59:59 (UTC)。"""
    today = date.today()
    # 本周一
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(weeks=1)
    last_sunday = this_monday - timedelta(days=1)
    start = datetime.combine(last_monday, time.min, tzinfo=timezone.utc)
    end = datetime.combine(last_sunday, time.max, tzinfo=timezone.utc).replace(microsecond=0)
    return start, end


def get_last_month_range() -> tuple[datetime, datetime]:
    """上月第一天 00:00:00 → 最后一天 23:59:59 (UTC)。"""
    today = date.today()
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    start = datetime.combine(first_day_last_month, time.min, tzinfo=timezone.utc)
    end = datetime.combine(last_day_last_month, time.max, tzinfo=timezone.utc).replace(microsecond=0)
    return start, end
