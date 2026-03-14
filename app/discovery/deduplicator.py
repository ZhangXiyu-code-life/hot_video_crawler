"""
视频去重器。
使用 Redis 布隆过滤器对发现阶段的候选视频去重，
避免同一视频被多个策略重复发现后重复入库。
"""
from app.datasource.schemas import VideoMeta
from app.utils.bloom_filter import BloomFilter
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VideoDeduplicator:

    def __init__(self, bloom_filter: BloomFilter) -> None:
        self._bloom = bloom_filter

    async def filter_new(self, videos: list[VideoMeta]) -> list[VideoMeta]:
        """
        过滤出未见过的新视频。
        同时将新视频标记到布隆过滤器，防止后续重复。
        """
        new_videos: list[VideoMeta] = []
        for video in videos:
            key = f"{video.platform}:{video.video_id}"
            if await self._bloom.is_new(key):
                new_videos.append(video)

        logger.info(
            "deduplication_done",
            total=len(videos),
            new=len(new_videos),
            duplicate=len(videos) - len(new_videos),
        )
        return new_videos
