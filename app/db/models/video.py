from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Video(Base):
    """追踪中的视频基本信息。"""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 平台标识
    platform: Mapped[str] = mapped_column(String(32), nullable=False)       # douyin | bilibili
    video_id: Mapped[str] = mapped_column(String(128), nullable=False)       # 平台原始视频 ID
    track: Mapped[str] = mapped_column(String(64), nullable=False)           # 赛道标签

    # 视频元信息
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    author_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    author_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    cover_url: Mapped[str] = mapped_column(Text, nullable=True)
    video_url: Mapped[str] = mapped_column(Text, nullable=True)

    # 分类元数据
    track_confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)
    classify_stage: Mapped[str] = mapped_column(String(32), nullable=False, default="rule")  # rule | tag | llm
    discovery_source: Mapped[str] = mapped_column(String(32), nullable=False, default="account")  # account | keyword | topic

    # 状态
    is_tracking: Mapped[bool] = mapped_column(nullable=False, default=True)

    # 时间
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # 关联
    snapshots: Mapped[list["VideoSnapshot"]] = relationship(back_populates="video", lazy="noload")  # noqa: F821

    __table_args__ = (
        # 平台 + 视频ID 联合唯一，防止重复入库
        Index("uq_platform_video_id", "platform", "video_id", unique=True),
        Index("ix_videos_track", "track"),
        Index("ix_videos_is_tracking", "is_tracking"),
    )

    def __repr__(self) -> str:
        return f"<Video platform={self.platform} video_id={self.video_id} track={self.track}>"
