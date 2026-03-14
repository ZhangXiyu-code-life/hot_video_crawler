"""
SnapshotCollector：快照采集器。

职责：
1. 从 DB 批量加载追踪中的视频（分批处理，每批 batch_size 条）
2. 调用 datasource.fetch_stats() 获取最新播放数据
3. 将 snapshot_at 对齐到整点小时（消除采集时间漂移）
4. 幂等写入 VideoSnapshot 表（ON CONFLICT DO NOTHING）

snapshot_at 时间对齐原则：
  实际采集时间 09:07 → 对齐为 09:00
  保证同一小时内无论几点采集，都写入同一时间锚点
  增量计算时取整点快照，结果稳定可预期
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.datasource.base import PlatformDataSource
from app.db.models.video import Video
from app.db.repositories.snapshot_repo import SnapshotRepository
from app.db.repositories.video_repo import VideoRepository
from app.utils.logging import get_logger
from app.utils.time_utils import floor_to_hour, now_utc

logger = get_logger(__name__)
settings = get_settings()


class SnapshotCollector:

    def __init__(
        self,
        datasource: PlatformDataSource,
        session: AsyncSession,
    ) -> None:
        self._datasource = datasource
        self._session = session
        self._video_repo = VideoRepository(session)
        self._snapshot_repo = SnapshotRepository(session)
        self._batch_size = settings.snapshot_batch_size

    async def collect_all(self, track: str | None = None) -> int:
        """
        采集追踪池中所有视频的快照。
        track: 指定赛道，None 则采集全部赛道。
        返回本次成功写入的快照数量。
        """
        snapshot_at = floor_to_hour(now_utc())
        logger.info("snapshot_collect_start", snapshot_at=snapshot_at, track=track)

        total_saved = 0
        offset = 0

        while True:
            # 分批加载追踪中的视频
            videos: list[Video] = await self._video_repo.get_tracked_videos(
                track=track,
                platform=self._datasource.platform,
                limit=self._batch_size,
                offset=offset,
            )

            if not videos:
                break

            saved = await self._collect_batch(videos, snapshot_at)
            total_saved += saved
            offset += self._batch_size

            logger.info(
                "snapshot_batch_done",
                offset=offset,
                batch_size=len(videos),
                saved=saved,
            )

            # 最后一批（不足 batch_size）则结束循环
            if len(videos) < self._batch_size:
                break

        await self._session.commit()
        logger.info("snapshot_collect_done", total_saved=total_saved, snapshot_at=snapshot_at)
        return total_saved

    async def _collect_batch(self, videos: list[Video], snapshot_at) -> int:
        """
        采集一批视频的快照数据。
        返回成功写入数量。
        """
        # 用平台原始 video_id 批量拉取数据
        platform_video_ids = [v.video_id for v in videos]

        try:
            stats_list = await self._datasource.fetch_stats(platform_video_ids)
        except Exception as e:
            logger.error("fetch_stats_failed", error=str(e), count=len(platform_video_ids))
            return 0

        # 构建 platform_video_id → DB video_id 映射
        id_map = {v.video_id: v.id for v in videos}

        # 构建批量插入数据
        rows = []
        for stats in stats_list:
            db_id = id_map.get(stats.video_id)
            if db_id is None:
                continue
            rows.append({
                "video_id": db_id,
                "play_count": stats.play_count,
                "like_count": stats.like_count,
                "comment_count": stats.comment_count,
                "share_count": stats.share_count,
                "collect_count": stats.collect_count,
                "snapshot_at": snapshot_at,
            })

        if rows:
            await self._snapshot_repo.bulk_insert(rows)

        return len(rows)
