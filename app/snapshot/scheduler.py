"""
APScheduler 调度器。

所有定时 Job 集中在此注册，生命周期由 FastAPI lifespan 管理。

Job 一览：
┌────────────────┬─────────────────┬───────────────────────────────┐
│ job_id         │ cron            │ 执行内容                       │
├────────────────┼─────────────────┼───────────────────────────────┤
│ discover       │ 0 */6 * * *     │ 每6h 发现新视频                │
│ snapshot_am    │ 5 0 * * *       │ 每日 00:05 快照                │
│ snapshot_pm    │ 5 12 * * *      │ 每日 12:05 快照                │
│ ranking_daily  │ 30 0 * * *      │ 每日 00:30 生成日榜            │
│ ranking_weekly │ 30 0 * * 1      │ 周一 00:30 生成周榜            │
│ ranking_monthly│ 30 0 1 * *      │ 每月1日 00:30 生成月榜         │
└────────────────┴─────────────────┴───────────────────────────────┘
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.utils.logging import get_logger

logger = get_logger(__name__)


def build_scheduler(
    datasource,
    session_factory,
    bloom_filter,
) -> AsyncIOScheduler:
    """
    构建并返回配置好所有 Job 的调度器实例。
    调用方负责 scheduler.start() 和 scheduler.shutdown()。
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # ── 视频发现任务 ─────────────────────────────────────────────
    scheduler.add_job(
        _job_discover,
        CronTrigger(hour="*/6", minute=0),
        id="discover",
        kwargs={
            "datasource": datasource,
            "session_factory": session_factory,
            "bloom_filter": bloom_filter,
        },
        max_instances=1,
        coalesce=True,          # 错过的执行合并为一次
        misfire_grace_time=300, # 允许延迟 5 分钟内补跑
    )

    # ── 快照采集任务（每日两次）──────────────────────────────────
    for job_id, hour, minute in [
        ("snapshot_am", 0, 5),
        ("snapshot_pm", 12, 5),
    ]:
        scheduler.add_job(
            _job_snapshot,
            CronTrigger(hour=hour, minute=minute),
            id=job_id,
            kwargs={
                "datasource": datasource,
                "session_factory": session_factory,
            },
            max_instances=1,
            coalesce=True,
            misfire_grace_time=600,
        )

    # ── 榜单生成任务 ─────────────────────────────────────────────
    ranking_jobs = [
        ("ranking_daily",   CronTrigger(hour=0, minute=30),             "daily"),
        ("ranking_weekly",  CronTrigger(day_of_week="mon", hour=0, minute=30), "weekly"),
        ("ranking_monthly", CronTrigger(day=1, hour=0, minute=30),      "monthly"),
    ]
    for job_id, trigger, period_type in ranking_jobs:
        scheduler.add_job(
            _job_ranking,
            trigger,
            id=job_id,
            kwargs={
                "period_type": period_type,
                "session_factory": session_factory,
            },
            max_instances=1,
            coalesce=True,
            misfire_grace_time=600,
        )

    return scheduler


# ── Job 函数 ──────────────────────────────────────────────────────

async def _job_discover(datasource, session_factory, bloom_filter) -> None:
    """视频发现 Job：对所有活跃赛道执行发现流程。"""
    from app.config import get_settings
    from app.discovery.engine import VideoDiscoveryEngine
    from app.utils.job_logger import record_job

    settings = get_settings()
    tracks = [
        t["name"]
        for t in settings.tracks_config.get("tracks", [])
        if t.get("is_active", True)
    ]

    async with session_factory() as session:
        async with record_job(session, "discover") as ctx:
            engine = VideoDiscoveryEngine(datasource, session, bloom_filter)
            results = {}
            for track_name in tracks:
                saved = await engine.run(track_name)
                results[track_name] = saved
                logger.info("job_discover_done", track=track_name, saved=saved)
            ctx["tracks"] = results
            ctx["total_saved"] = sum(results.values())


async def _job_snapshot(datasource, session_factory) -> None:
    """快照采集 Job：对所有追踪视频拍一次快照。"""
    from app.snapshot.collector import SnapshotCollector
    from app.utils.job_logger import record_job

    async with session_factory() as session:
        async with record_job(session, "snapshot") as ctx:
            collector = SnapshotCollector(datasource, session)
            total = await collector.collect_all()
            ctx["snapshots"] = total
            logger.info("job_snapshot_done", total=total)


async def _job_ranking(period_type: str, session_factory) -> None:
    """榜单生成 Job：对所有活跃赛道生成指定周期的榜单。"""
    from app.config import get_settings
    from app.ranking.generator import RankingGenerator
    from app.ranking.periods import PeriodType
    from app.utils.job_logger import record_job

    settings = get_settings()
    tracks = [
        t["name"]
        for t in settings.tracks_config.get("tracks", [])
        if t.get("is_active", True)
    ]

    async with session_factory() as session:
        async with record_job(session, f"ranking_{period_type}") as ctx:
            generator = RankingGenerator(session)
            for track_name in tracks:
                await generator.generate(PeriodType(period_type), track_name)
                logger.info("job_ranking_done", period=period_type, track=track_name)
            ctx["period"] = period_type
            ctx["tracks"] = tracks
