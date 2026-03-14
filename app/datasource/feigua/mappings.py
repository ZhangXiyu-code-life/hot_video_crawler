"""
飞瓜数据字段 → 标准模型映射。

TODO: 拿到 API 文档后，根据真实返回字段调整 key 名称。
      当前为占位实现，字段名以 feigua_* 开头表示待确认。
"""
from datetime import datetime, timezone

from app.datasource.schemas import VideoMeta, VideoStats


def map_video_meta(raw: dict) -> VideoMeta:
    """飞瓜视频基本信息 → VideoMeta。"""
    published_ts = raw.get("feigua_publish_time")
    published_at = (
        datetime.fromtimestamp(published_ts, tz=timezone.utc)
        if published_ts
        else None
    )
    return VideoMeta(
        video_id=str(raw["feigua_video_id"]),
        platform="douyin",
        title=raw.get("feigua_title", ""),
        author_id=str(raw.get("feigua_author_id", "")),
        author_name=raw.get("feigua_author_name", ""),
        author_bio=raw.get("feigua_author_bio", ""),
        cover_url=raw.get("feigua_cover_url"),
        video_url=raw.get("feigua_video_url"),
        published_at=published_at,
        tags=raw.get("feigua_tags", []),
        description=raw.get("feigua_description", ""),
    )


def map_video_stats(raw: dict) -> VideoStats:
    """飞瓜视频数据 → VideoStats。"""
    return VideoStats(
        video_id=str(raw["feigua_video_id"]),
        platform="douyin",
        play_count=int(raw.get("feigua_play_count", 0)),
        like_count=int(raw.get("feigua_like_count", 0)),
        comment_count=int(raw.get("feigua_comment_count", 0)),
        share_count=int(raw.get("feigua_share_count", 0)),
        collect_count=int(raw.get("feigua_collect_count", 0)),
        fetched_at=datetime.now(tz=timezone.utc),
    )
