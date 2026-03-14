from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Track(Base):
    """
    赛道配置（同步自 config/tracks.yaml）。
    支持热更新：修改 yaml 后运行 scripts/init_tracks.py 即可更新。
    """

    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)   # knowledge_course
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)       # 知识传播/卖课
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    keywords_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")    # JSON array
    topic_tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    llm_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")    # 赛道分类 Prompt
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Track name={self.name} active={self.is_active}>"
