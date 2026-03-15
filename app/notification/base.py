from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RankingResult:
    """通知层使用的榜单数据结构（与 DB Model 解耦）。"""
    period_type: str          # daily | weekly | monthly
    platform: str
    track: str
    track_display_name: str
    period_start: str         # ISO date string
    period_end: str
    items: list[dict] = field(default_factory=list)
    # items 每条：{rank, video_title, author_name, play_increment, play_count_end, cover_url}


class NotificationChannel(ABC):
    """通知渠道抽象接口。新增渠道只需实现此接口并注册到 dispatcher。"""

    @abstractmethod
    async def send(self, result: RankingResult) -> bool:
        """发送通知，返回是否成功。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """渠道名称，用于日志标识。"""
