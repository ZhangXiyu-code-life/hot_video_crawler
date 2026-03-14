from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.ranking import Ranking, RankingItem


class RankingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_ranking(
        self,
        period_type: str,
        platform: str,
        track: str,
        period_start: date,
        period_end: date,
        top_n: int,
    ) -> Ranking:
        stmt = (
            insert(Ranking)
            .values(
                period_type=period_type,
                platform=platform,
                track=track,
                period_start=period_start,
                period_end=period_end,
                top_n=top_n,
            )
            .on_conflict_do_update(
                index_elements=["period_type", "platform", "track", "period_start"],
                set_={"period_end": period_end, "top_n": top_n},
            )
            .returning(Ranking)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one()

    async def replace_items(self, ranking_id: int, items: list[dict]) -> None:
        """删除旧条目，写入新条目（榜单重算时使用）。"""
        from sqlalchemy import delete
        await self._session.execute(
            delete(RankingItem).where(RankingItem.ranking_id == ranking_id)
        )
        if items:
            await self._session.execute(
                insert(RankingItem).values([{"ranking_id": ranking_id, **item} for item in items])
            )

    async def get_latest(
        self,
        period_type: str,
        track: str,
        platform: str = "douyin",
    ) -> Ranking | None:
        stmt = (
            select(Ranking)
            .where(
                Ranking.period_type == period_type,
                Ranking.track == track,
                Ranking.platform == platform,
            )
            .order_by(Ranking.period_start.desc())
            .limit(1)
            .options(selectinload(Ranking.items))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_history(
        self,
        period_type: str,
        track: str,
        platform: str = "douyin",
        limit: int = 10,
    ) -> list[Ranking]:
        stmt = (
            select(Ranking)
            .where(
                Ranking.period_type == period_type,
                Ranking.track == track,
                Ranking.platform == platform,
            )
            .order_by(Ranking.period_start.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
