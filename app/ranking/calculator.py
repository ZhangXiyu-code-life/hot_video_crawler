"""
IncrementCalculator：播放量增量计算器。

核心逻辑：
  1. 取 period_start 时间点之后最近的快照（期初值）
  2. 取 period_end 时间点之前最近的快照（期末值）
  3. delta = end.play_count - start.play_count

边界处理：
  - 期初或期末无快照 → 返回 0（视频追踪时间不足，无法计算）
  - delta < 0（数据回撤/平台修正）→ 返回 0
"""
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.snapshot_repo import SnapshotRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)


class IncrementCalculator:

    def __init__(self, session: AsyncSession) -> None:
        self._repo = SnapshotRepository(session)

    async def calc(
        self,
        video_db_id: int,
        period_start: datetime,
        period_end: datetime,
    ) -> int:
        """
        计算视频在 [period_start, period_end] 内的播放量增量。
        返回增量值（≥ 0）。
        """
        # 期初快照：period_start 之后最近的一条
        start_snap = await self._repo.get_snapshot_at(
            video_db_id, period_start, direction="after"
        )
        # 期末快照：period_end 之前最近的一条
        end_snap = await self._repo.get_snapshot_at(
            video_db_id, period_end, direction="before"
        )

        if start_snap is None or end_snap is None:
            return 0

        # 两条快照是同一条（视频追踪时间短，只有一次快照）
        if start_snap.id == end_snap.id:
            return 0

        delta = end_snap.play_count - start_snap.play_count
        if delta < 0:
            logger.warning(
                "negative_increment",
                video_id=video_db_id,
                start=start_snap.play_count,
                end=end_snap.play_count,
            )
            return 0

        return delta

    async def calc_batch(
        self,
        video_db_ids: list[int],
        period_start: datetime,
        period_end: datetime,
        concurrency: int = 20,
    ) -> dict[int, int]:
        """
        批量计算多个视频的增量，限制并发数避免数据库连接压力。
        返回 {video_db_id: increment} 字典。
        """
        import asyncio

        semaphore = asyncio.Semaphore(concurrency)

        async def _calc_one(vid: int) -> tuple[int, int]:
            async with semaphore:
                increment = await self.calc(vid, period_start, period_end)
                return vid, increment

        results = await asyncio.gather(*[_calc_one(vid) for vid in video_db_ids])
        return dict(results)
