"""
头部账号追踪策略。
遍历账号白名单，拉取各账号的近期视频。
覆盖度：高；精度：高（白名单已人工确认赛道）。
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.datasource.base import PlatformDataSource
from app.datasource.schemas import VideoMeta
from app.db.models.account import AccountWhitelist
from app.discovery.strategies.base import DiscoveryStrategy
from app.utils.logging import get_logger
from sqlalchemy import select

logger = get_logger(__name__)


class AccountStrategy(DiscoveryStrategy):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def name(self) -> str:
        return "account"

    async def run(
        self,
        datasource: PlatformDataSource,
        track_name: str,
        config: dict,
    ) -> list[VideoMeta]:
        # 从 DB 加载该赛道的活跃账号白名单
        stmt = select(AccountWhitelist).where(
            AccountWhitelist.track == track_name,
            AccountWhitelist.platform == datasource.platform,
            AccountWhitelist.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        accounts = list(result.scalars().all())

        if not accounts:
            logger.warning("account_strategy_no_accounts", track=track_name)
            return []

        videos: list[VideoMeta] = []
        for account in accounts:
            try:
                account_videos = await datasource.get_account_videos(
                    account_id=account.account_id, limit=30
                )
                videos.extend(account_videos)
            except Exception as e:
                logger.error(
                    "account_strategy_fetch_failed",
                    account_id=account.account_id,
                    error=str(e),
                )

        logger.info(
            "account_strategy_done",
            track=track_name,
            accounts=len(accounts),
            videos=len(videos),
        )
        return videos
