from abc import ABC, abstractmethod

from app.datasource.base import PlatformDataSource
from app.datasource.schemas import VideoMeta


class DiscoveryStrategy(ABC):
    """
    视频发现策略抽象接口。
    每种策略负责从不同入口发现候选视频，返回标准 VideoMeta 列表。
    """

    @abstractmethod
    async def run(
        self,
        datasource: PlatformDataSource,
        track_name: str,
        config: dict,
    ) -> list[VideoMeta]:
        """
        执行发现任务。
        track_name: 目标赛道名称（如 knowledge_course）
        config: 来自 tracks.yaml 的赛道配置（keywords, topic_tags 等）
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称，用于日志标识。"""
