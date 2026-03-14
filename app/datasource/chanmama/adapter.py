"""
蝉妈妈数据适配器（骨架）。
TODO: 拿到 API 文档后填入真实实现。
"""
from app.datasource.base import PlatformDataSource
from app.datasource.schemas import VideoMeta, VideoStats


class ChanmamaDataSource(PlatformDataSource):

    @property
    def platform(self) -> str:
        return "douyin"

    async def search_by_keyword(self, keyword: str, limit: int = 50) -> list[VideoMeta]:
        raise NotImplementedError("蝉妈妈 search_by_keyword 接口待实现")

    async def get_topic_videos(self, topic_tag: str, limit: int = 50) -> list[VideoMeta]:
        raise NotImplementedError("蝉妈妈 get_topic_videos 接口待实现")

    async def get_account_videos(self, account_id: str, limit: int = 30) -> list[VideoMeta]:
        raise NotImplementedError("蝉妈妈 get_account_videos 接口待实现")

    async def fetch_stats(self, video_ids: list[str]) -> list[VideoStats]:
        raise NotImplementedError("蝉妈妈 fetch_stats 接口待实现")
