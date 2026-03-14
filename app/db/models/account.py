from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountWhitelist(Base):
    """
    头部账号白名单。
    由人工维护 + 系统自动扩充（当一个账号的视频持续上榜时自动加入）。
    """

    __tablename__ = "account_whitelist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    platform: Mapped[str] = mapped_column(String(32), nullable=False)       # douyin
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)    # 平台原始账号 ID
    account_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    track: Mapped[str] = mapped_column(String(64), nullable=False)          # 账号主要赛道

    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")  # manual | auto

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("uq_account_platform_id", "platform", "account_id", unique=True),
        Index("ix_account_track", "track"),
        Index("ix_account_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<AccountWhitelist platform={self.platform} account_id={self.account_id} track={self.track}>"
