"""
数据源标准数据模型。

所有平台适配器的输入输出都使用这里定义的模型，
上层业务逻辑与平台无关。
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VideoMeta:
    """视频基本信息（发现阶段使用）。"""
    video_id: str                          # 平台原始视频 ID
    platform: str                          # douyin | bilibili | youtube
    title: str
    author_id: str
    author_name: str
    cover_url: str | None = None
    video_url: str | None = None
    published_at: datetime | None = None
    tags: list[str] = field(default_factory=list)
    description: str = ""
    author_bio: str = ""                   # 账号简介（用于 LLM 分类）


@dataclass
class VideoStats:
    """视频播放数据（快照阶段使用）。"""
    video_id: str                          # 平台原始视频 ID
    platform: str
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    collect_count: int = 0
    fetched_at: datetime = field(default_factory=datetime.utcnow)
