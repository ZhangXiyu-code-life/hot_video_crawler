from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.video import TrackResponse
from app.db.models.track import Track

router = APIRouter(prefix="/tracks", tags=["赛道"])


@router.get("", response_model=list[TrackResponse])
async def list_tracks(db: AsyncSession = Depends(get_db)):
    """获取所有已配置的赛道列表。"""
    result = await db.execute(select(Track).where(Track.is_active.is_(True)))
    return list(result.scalars().all())
