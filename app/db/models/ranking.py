from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Ranking(Base):
    """
    榜单主表，记录每期榜单的元信息。
    period_type: daily | weekly | monthly
    """

    __tablename__ = "rankings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    period_type: Mapped[str] = mapped_column(String(16), nullable=False)   # daily | weekly | monthly
    platform: Mapped[str] = mapped_column(String(32), nullable=False)      # douyin
    track: Mapped[str] = mapped_column(String(64), nullable=False)         # knowledge_course

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    top_n: Mapped[int] = mapped_column(Integer, nullable=False)            # 10 or 20
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    items: Mapped[list["RankingItem"]] = relationship(
        back_populates="ranking",
        lazy="noload",
        order_by="RankingItem.rank",
    )

    __table_args__ = (
        Index("uq_ranking_period", "period_type", "platform", "track", "period_start", unique=True),
        Index("ix_ranking_track_period", "track", "period_type", "period_start"),
    )

    def __repr__(self) -> str:
        return f"<Ranking {self.period_type} {self.track} {self.period_start}~{self.period_end}>"


class RankingItem(Base):
    """榜单条目，记录每个上榜视频的排名和增量数据。"""

    __tablename__ = "ranking_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ranking_id: Mapped[int] = mapped_column(
        ForeignKey("rankings.id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )

    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    play_increment: Mapped[int] = mapped_column(BigInteger, nullable=False)  # 周期内增量播放数
    play_count_end: Mapped[int] = mapped_column(BigInteger, nullable=False)  # 期末绝对播放数

    # 冗余存储视频信息（防止视频被删后榜单数据丢失）
    video_platform_id: Mapped[str] = mapped_column(String(128), nullable=False)
    video_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    author_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    cover_url: Mapped[str] = mapped_column(Text, nullable=True)

    ranking: Mapped["Ranking"] = relationship(back_populates="items", lazy="noload")

    __table_args__ = (
        Index("ix_ranking_items_ranking_id", "ranking_id"),
    )
