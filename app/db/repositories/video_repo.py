from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.video import Video


class VideoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, platform: str, video_id: str, **kwargs) -> Video:
        """插入或更新视频信息，以 (platform, video_id) 为唯一键。"""
        stmt = (
            insert(Video)
            .values(platform=platform, video_id=video_id, **kwargs)
            .on_conflict_do_update(
                index_elements=["platform", "video_id"],
                set_={k: v for k, v in kwargs.items() if k not in ("created_at",)},
            )
            .returning(Video)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one()

    async def get_tracked_videos(
        self,
        track: str | None = None,
        platform: str = "douyin",
        limit: int = 10_000,
        offset: int = 0,
    ) -> list[Video]:
        """获取追踪中的视频列表，用于快照采集。"""
        stmt = select(Video).where(Video.is_tracking.is_(True))
        if platform:
            stmt = stmt.where(Video.platform == platform)
        if track:
            stmt = stmt.where(Video.track == track)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_platform_id(self, platform: str, video_id: str) -> Video | None:
        stmt = select(Video).where(
            Video.platform == platform,
            Video.video_id == video_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate(self, platform: str, video_id: str) -> None:
        stmt = (
            update(Video)
            .where(Video.platform == platform, Video.video_id == video_id)
            .values(is_tracking=False)
        )
        await self._session.execute(stmt)
