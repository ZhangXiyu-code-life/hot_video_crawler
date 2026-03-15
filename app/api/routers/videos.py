from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.common import PaginatedResponse
from app.api.schemas.video import VideoResponse
from app.db.repositories.video_repo import VideoRepository

router = APIRouter(prefix="/videos", tags=["视频"])


@router.get("", response_model=PaginatedResponse[VideoResponse])
async def list_videos(
    track: str | None = None,
    platform: str = "douyin",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """获取追踪中的视频列表，支持按赛道和平台过滤。"""
    repo = VideoRepository(db)
    videos = await repo.get_tracked_videos(
        track=track, platform=platform, limit=limit, offset=offset
    )
    return PaginatedResponse(total=len(videos), items=videos)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    platform: str = "douyin",
    db: AsyncSession = Depends(get_db),
):
    """获取单个视频详情。"""
    repo = VideoRepository(db)
    video = await repo.get_by_platform_id(platform, video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"视频不存在：{video_id}")
    return video
