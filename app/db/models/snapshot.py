from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VideoSnapshot(Base):
    """
    视频播放数据快照（时序表）。

    每次采集时对追踪池中所有视频打一次快照，
    增量计算通过对比两个时间点的 play_count 实现。

    存储规模：~35,000 视频 × 2次/天 = 70,000 行/天，约 5GB/年。
    建议按月对 snapshot_at 列创建分区索引。
    """

    __tablename__ = "video_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )

    # 播放数据
    play_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    share_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    collect_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # 快照时间（精确到整点小时，消除采集漂移）
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # 关联
    video: Mapped["Video"] = relationship(back_populates="snapshots", lazy="noload")  # noqa: F821

    __table_args__ = (
        # 幂等约束：同一视频同一快照时间只能有一条记录
        Index("uq_snapshot_video_time", "video_id", "snapshot_at", unique=True),
        # 增量计算高频查询索引
        Index("ix_snapshots_video_time", "video_id", "snapshot_at"),
        Index("ix_snapshots_time", "snapshot_at"),
    )

    def __repr__(self) -> str:
        return f"<VideoSnapshot video_id={self.video_id} play_count={self.play_count} at={self.snapshot_at}>"
