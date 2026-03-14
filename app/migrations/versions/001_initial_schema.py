"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tracks ────────────────────────────────────────────────────────────────
    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("keywords_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("topic_tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("llm_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── account_whitelist ─────────────────────────────────────────────────────
    op.create_table(
        "account_whitelist",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("account_id", sa.String(128), nullable=False),
        sa.Column("account_name", sa.String(256), nullable=False, server_default=""),
        sa.Column("track", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("uq_account_platform_id", "account_whitelist", ["platform", "account_id"], unique=True)
    op.create_index("ix_account_track", "account_whitelist", ["track"])
    op.create_index("ix_account_is_active", "account_whitelist", ["is_active"])

    # ── videos ────────────────────────────────────────────────────────────────
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("video_id", sa.String(128), nullable=False),
        sa.Column("track", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("author_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("author_name", sa.String(256), nullable=False, server_default=""),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("track_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("classify_stage", sa.String(32), nullable=False, server_default="rule"),
        sa.Column("discovery_source", sa.String(32), nullable=False, server_default="account"),
        sa.Column("is_tracking", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("uq_platform_video_id", "videos", ["platform", "video_id"], unique=True)
    op.create_index("ix_videos_track", "videos", ["track"])
    op.create_index("ix_videos_is_tracking", "videos", ["is_tracking"])

    # ── video_snapshots ───────────────────────────────────────────────────────
    op.create_table(
        "video_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("play_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("like_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("share_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("collect_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("uq_snapshot_video_time", "video_snapshots", ["video_id", "snapshot_at"], unique=True)
    op.create_index("ix_snapshots_video_time", "video_snapshots", ["video_id", "snapshot_at"])
    op.create_index("ix_snapshots_time", "video_snapshots", ["snapshot_at"])

    # ── rankings ──────────────────────────────────────────────────────────────
    op.create_table(
        "rankings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("period_type", sa.String(16), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("track", sa.String(64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("top_n", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "uq_ranking_period", "rankings",
        ["period_type", "platform", "track", "period_start"], unique=True
    )
    op.create_index("ix_ranking_track_period", "rankings", ["track", "period_type", "period_start"])

    # ── ranking_items ─────────────────────────────────────────────────────────
    op.create_table(
        "ranking_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ranking_id", sa.Integer(), sa.ForeignKey("rankings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("play_increment", sa.BigInteger(), nullable=False),
        sa.Column("play_count_end", sa.BigInteger(), nullable=False),
        sa.Column("video_platform_id", sa.String(128), nullable=False),
        sa.Column("video_title", sa.Text(), nullable=False, server_default=""),
        sa.Column("author_name", sa.String(256), nullable=False, server_default=""),
        sa.Column("cover_url", sa.Text(), nullable=True),
    )
    op.create_index("ix_ranking_items_ranking_id", "ranking_items", ["ranking_id"])


def downgrade() -> None:
    op.drop_table("ranking_items")
    op.drop_table("rankings")
    op.drop_table("video_snapshots")
    op.drop_table("videos")
    op.drop_table("account_whitelist")
    op.drop_table("tracks")
