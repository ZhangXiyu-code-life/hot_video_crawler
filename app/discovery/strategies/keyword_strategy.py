"""
关键词搜索策略。
遍历赛道关键词列表，逐词搜索并合并结果。
覆盖度：中；精度：中（搜索结果需经分类器过滤）。
"""
from app.datasource.base import PlatformDataSource
from app.datasource.schemas import VideoMeta
from app.discovery.strategies.base import DiscoveryStrategy
from app.utils.logging import get_logger

logger = get_logger(__name__)


class KeywordStrategy(DiscoveryStrategy):

    @property
    def name(self) -> str:
        return "keyword"

    async def run(
        self,
        datasource: PlatformDataSource,
        track_name: str,
        config: dict,
    ) -> list[VideoMeta]:
        keywords: list[str] = config.get("keywords", [])

        if not keywords:
            logger.warning("keyword_strategy_no_keywords", track=track_name)
            return []

        videos: list[VideoMeta] = []
        for keyword in keywords:
            try:
                results = await datasource.search_by_keyword(keyword, limit=30)
                videos.extend(results)
            except Exception as e:
                logger.error(
                    "keyword_strategy_fetch_failed",
                    keyword=keyword,
                    error=str(e),
                )

        logger.info(
            "keyword_strategy_done",
            track=track_name,
            keywords=len(keywords),
            videos=len(videos),
        )
        return videos
