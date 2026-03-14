"""
话题/挑战赛发现策略。
遍历赛道关联的话题标签，拉取话题下的视频列表。
覆盖度：中；精度：中。
"""
from app.datasource.base import PlatformDataSource
from app.datasource.schemas import VideoMeta
from app.discovery.strategies.base import DiscoveryStrategy
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TopicStrategy(DiscoveryStrategy):

    @property
    def name(self) -> str:
        return "topic"

    async def run(
        self,
        datasource: PlatformDataSource,
        track_name: str,
        config: dict,
    ) -> list[VideoMeta]:
        topic_tags: list[str] = config.get("topic_tags", [])

        if not topic_tags:
            logger.warning("topic_strategy_no_tags", track=track_name)
            return []

        videos: list[VideoMeta] = []
        for tag in topic_tags:
            try:
                results = await datasource.get_topic_videos(tag, limit=30)
                videos.extend(results)
            except Exception as e:
                logger.error(
                    "topic_strategy_fetch_failed",
                    tag=tag,
                    error=str(e),
                )

        logger.info(
            "topic_strategy_done",
            track=track_name,
            tags=len(topic_tags),
            videos=len(videos),
        )
        return videos
