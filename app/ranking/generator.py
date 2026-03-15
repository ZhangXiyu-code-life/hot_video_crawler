"""
RankingGenerator：榜单生成器。

流程：
1. 确定周期时间范围
2. 加载该赛道所有追踪视频
3. 批量计算每个视频的播放增量
4. 按增量降序排序，取 Top N
5. 持久化榜单到 DB
6. 触发通知（Phase 6 接入）
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.video import Video
from app.db.repositories.ranking_repo import RankingRepository
from app.notification.base import RankingResult
from app.notification.dispatcher import NotificationDispatcher
from app.db.repositories.snapshot_repo import SnapshotRepository
from app.db.repositories.video_repo import VideoRepository
from app.ranking.calculator import IncrementCalculator
from app.ranking.periods import PERIOD_TOP_N, PeriodType, get_period_dates, get_period_range
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RankingGenerator:

    def __init__(
        self,
        session: AsyncSession,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        self._session = session
        self._dispatcher = dispatcher
        self._video_repo = VideoRepository(session)
        self._ranking_repo = RankingRepository(session)
        self._calculator = IncrementCalculator(session)

    async def generate(
        self,
        period_type: PeriodType,
        track_name: str,
        platform: str = "douyin",
    ) -> None:
        """
        生成指定周期和赛道的榜单，写入 DB 并触发通知。
        """
        period_start_dt, period_end_dt = get_period_range(period_type)
        period_start_date, period_end_date = get_period_dates(period_type)
        top_n = PERIOD_TOP_N[period_type]

        logger.info(
            "ranking_generate_start",
            period=period_type,
            track=track_name,
            start=period_start_dt,
            end=period_end_dt,
        )

        # 加载追踪视频
        videos: list[Video] = await self._video_repo.get_tracked_videos(
            track=track_name,
            platform=platform,
            limit=100_000,
        )

        if not videos:
            logger.warning("ranking_no_videos", track=track_name, period=period_type)
            return

        # 批量计算增量
        video_db_ids = [v.id for v in videos]
        increment_map = await self._calculator.calc_batch(
            video_db_ids, period_start_dt, period_end_dt
        )

        # 过滤掉增量为 0 的视频（没有足够快照），然后排序
        ranked = sorted(
            [(v, increment_map.get(v.id, 0)) for v in videos if increment_map.get(v.id, 0) > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]

        if not ranked:
            logger.warning(
                "ranking_no_data",
                track=track_name,
                period=period_type,
                reason="所有视频增量为0，快照数据可能不足",
            )
            return

        # 获取期末快照的绝对播放量（用于展示）
        snapshot_repo = SnapshotRepository(self._session)
        ranking_items = []
        for rank_idx, (video, increment) in enumerate(ranked, start=1):
            end_snap = await snapshot_repo.get_snapshot_at(
                video.id, period_end_dt, direction="before"
            )
            ranking_items.append({
                "rank": rank_idx,
                "play_increment": increment,
                "play_count_end": end_snap.play_count if end_snap else 0,
                "video_platform_id": video.video_id,
                "video_title": video.title,
                "author_name": video.author_name,
                "cover_url": video.cover_url,
                "video_id": video.id,
            })

        # 写入 DB
        ranking = await self._ranking_repo.upsert_ranking(
            period_type=period_type.value,
            platform=platform,
            track=track_name,
            period_start=period_start_date,
            period_end=period_end_date,
            top_n=top_n,
        )
        await self._ranking_repo.replace_items(ranking.id, ranking_items)
        await self._session.commit()

        logger.info(
            "ranking_generate_done",
            period=period_type,
            track=track_name,
            items=len(ranking_items),
            top1_increment=ranking_items[0]["play_increment"] if ranking_items else 0,
        )

        # 触发通知
        if self._dispatcher:
            track_display = self._get_track_display_name(track_name)
            notification_result = RankingResult(
                period_type=period_type.value,
                platform=platform,
                track=track_name,
                track_display_name=track_display,
                period_start=str(period_start_date),
                period_end=str(period_end_date),
                items=ranking_items,
            )
            await self._dispatcher.dispatch(notification_result)

    def _get_track_display_name(self, track_name: str) -> str:
        from app.config import get_settings
        settings = get_settings()
        for track in settings.tracks_config.get("tracks", []):
            if track["name"] == track_name:
                return track.get("display_name", track_name)
        return track_name
