"""
飞瓜数据适配器。

TODO: 拿到 API 文档后填入真实接口路径和参数。
      当前各方法抛出 NotImplementedError，
      替换为真实实现后无需改动上层任何代码。
"""
from app.datasource.base import PlatformDataSource
from app.datasource.feigua.client import FeiguaClient
from app.datasource.feigua.mappings import map_video_meta, map_video_stats
from app.datasource.schemas import VideoMeta, VideoStats
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FeiguaDataSource(PlatformDataSource):

    def __init__(self, redis_client) -> None:
        self._client = FeiguaClient(redis_client)

    @property
    def platform(self) -> str:
        return "douyin"

    async def search_by_keyword(
        self, keyword: str, limit: int = 50
    ) -> list[VideoMeta]:
        # TODO: 填入飞瓜关键词搜索接口路径和参数
        # raw = await self._client.get("/v1/search/video", params={"keyword": keyword, "limit": limit})
        # return [map_video_meta(item) for item in raw.get("data", {}).get("list", [])]
        raise NotImplementedError("飞瓜 search_by_keyword 接口待实现")

    async def get_topic_videos(
        self, topic_tag: str, limit: int = 50
    ) -> list[VideoMeta]:
        # TODO: 填入飞瓜话题视频接口
        raise NotImplementedError("飞瓜 get_topic_videos 接口待实现")

    async def get_account_videos(
        self, account_id: str, limit: int = 30
    ) -> list[VideoMeta]:
        # TODO: 填入飞瓜账号视频列表接口
        raise NotImplementedError("飞瓜 get_account_videos 接口待实现")

    async def fetch_stats(
        self, video_ids: list[str]
    ) -> list[VideoStats]:
        # TODO: 填入飞瓜视频数据批量查询接口
        raise NotImplementedError("飞瓜 fetch_stats 接口待实现")
