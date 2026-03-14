"""
PlatformDataSource 抽象接口。

新增平台只需实现此接口并注册到 factory.py，上层零改动。
"""
from abc import ABC, abstractmethod

from app.datasource.schemas import VideoMeta, VideoStats


class PlatformDataSource(ABC):

    @abstractmethod
    async def search_by_keyword(
        self, keyword: str, limit: int = 50
    ) -> list[VideoMeta]:
        """按关键词搜索视频，用于关键词发现策略。"""

    @abstractmethod
    async def get_topic_videos(
        self, topic_tag: str, limit: int = 50
    ) -> list[VideoMeta]:
        """获取话题/挑战赛下的视频列表，用于话题发现策略。"""

    @abstractmethod
    async def get_account_videos(
        self, account_id: str, limit: int = 30
    ) -> list[VideoMeta]:
        """获取指定账号的视频列表，用于账号追踪策略。"""

    @abstractmethod
    async def fetch_stats(
        self, video_ids: list[str]
    ) -> list[VideoStats]:
        """
        批量获取视频播放数据，用于快照采集。
        video_ids: 平台原始视频 ID 列表。
        """

    @property
    @abstractmethod
    def platform(self) -> str:
        """平台标识，如 'douyin'。"""
