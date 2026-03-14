from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.snapshot import VideoSnapshot


class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_snapshot(
        self,
        video_id: int,
        play_count: int,
        like_count: int,
        comment_count: int,
        share_count: int,
        collect_count: int,
        snapshot_at: datetime,
    ) -> None:
        """幂等写入快照，同一视频同一时间点的快照忽略重复。"""
        stmt = (
            insert(VideoSnapshot)
            .values(
                video_id=video_id,
                play_count=play_count,
                like_count=like_count,
                comment_count=comment_count,
                share_count=share_count,
                collect_count=collect_count,
                snapshot_at=snapshot_at,
            )
            .on_conflict_do_nothing(index_elements=["video_id", "snapshot_at"])
        )
        await self._session.execute(stmt)

    async def get_snapshot_at(
        self,
        video_id: int,
        target_time: datetime,
        direction: str = "before",  # before | after
    ) -> VideoSnapshot | None:
        """
        获取指定时间点附近的快照。
        direction='before': 取 <= target_time 的最新快照（用于计算期末值）
        direction='after':  取 >= target_time 的最早快照（用于计算期初值）
        """
        if direction == "before":
            stmt = (
                select(VideoSnapshot)
                .where(
                    VideoSnapshot.video_id == video_id,
                    VideoSnapshot.snapshot_at <= target_time,
                )
                .order_by(VideoSnapshot.snapshot_at.desc())
                .limit(1)
            )
        else:
            stmt = (
                select(VideoSnapshot)
                .where(
                    VideoSnapshot.video_id == video_id,
                    VideoSnapshot.snapshot_at >= target_time,
                )
                .order_by(VideoSnapshot.snapshot_at.asc())
                .limit(1)
            )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_insert(self, snapshots: list[dict]) -> None:
        """批量插入快照，忽略重复。"""
        if not snapshots:
            return
        stmt = insert(VideoSnapshot).values(snapshots).on_conflict_do_nothing(
            index_elements=["video_id", "snapshot_at"]
        )
        await self._session.execute(stmt)
