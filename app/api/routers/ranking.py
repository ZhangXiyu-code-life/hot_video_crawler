from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.ranking import RankingListResponse, RankingResponse
from app.db.repositories.ranking_repo import RankingRepository
from app.ranking.periods import PeriodType

router = APIRouter(prefix="/ranking", tags=["榜单"])


@router.get("/{period_type}/{track}", response_model=RankingResponse)
async def get_latest_ranking(
    period_type: PeriodType,
    track: str,
    platform: str = "douyin",
    db: AsyncSession = Depends(get_db),
):
    """获取指定周期和赛道的最新一期榜单（含完整条目）。"""
    repo = RankingRepository(db)
    ranking = await repo.get_latest(period_type.value, track, platform)
    if not ranking:
        raise HTTPException(
            status_code=404,
            detail=f"暂无榜单数据：{period_type.value} / {track}，请等待首次生成。",
        )
    return ranking


@router.get("/history/{period_type}/{track}", response_model=RankingListResponse)
async def get_ranking_history(
    period_type: PeriodType,
    track: str,
    platform: str = "douyin",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """获取指定周期和赛道的历史榜单列表（不含条目详情）。"""
    repo = RankingRepository(db)
    rankings = await repo.list_history(period_type.value, track, platform, limit)
    return RankingListResponse(total=len(rankings), rankings=rankings)
