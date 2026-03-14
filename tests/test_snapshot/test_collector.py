"""
SnapshotCollector 单元测试。
使用 Mock 数据源 + 内存中的 DB 对象验证核心逻辑，
不依赖真实数据库连接。
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.datasource.schemas import VideoStats
from app.snapshot.collector import SnapshotCollector
from app.utils.time_utils import floor_to_hour, now_utc


# ── 测试 time_utils（无外部依赖）──────────────────────────────────

def test_floor_to_hour_truncates_minutes():
    dt = datetime(2026, 3, 14, 9, 37, 45, tzinfo=timezone.utc)
    result = floor_to_hour(dt)
    assert result.minute == 0
    assert result.second == 0
    assert result.microsecond == 0
    assert result.hour == 9


def test_floor_to_hour_already_on_hour():
    dt = datetime(2026, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert floor_to_hour(dt) == dt


def test_now_utc_is_timezone_aware():
    result = now_utc()
    assert result.tzinfo is not None


# ── 测试 SnapshotCollector ────────────────────────────────────────

def make_mock_video(db_id: int, platform_video_id: str):
    v = MagicMock()
    v.id = db_id
    v.video_id = platform_video_id
    return v


def make_mock_stats(video_id: str, play_count: int) -> VideoStats:
    return VideoStats(
        video_id=video_id,
        platform="douyin",
        play_count=play_count,
        like_count=100,
        comment_count=10,
        share_count=20,
        collect_count=50,
    )


@pytest.fixture
def mock_datasource():
    ds = AsyncMock()
    ds.platform = "douyin"
    ds.fetch_stats.return_value = [
        make_mock_stats("v001", 100_000),
        make_mock_stats("v002", 200_000),
    ]
    return ds


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.mark.asyncio
async def test_collect_all_calls_fetch_stats(mock_datasource, mock_session):
    videos = [
        make_mock_video(1, "v001"),
        make_mock_video(2, "v002"),
    ]

    collector = SnapshotCollector(mock_datasource, mock_session)

    with patch.object(collector._video_repo, "get_tracked_videos", new_callable=AsyncMock) as mock_get, \
         patch.object(collector._snapshot_repo, "bulk_insert", new_callable=AsyncMock) as mock_insert:

        # 第一批返回2条，第二批返回空（结束循环）
        mock_get.side_effect = [videos, []]
        mock_insert.return_value = None

        total = await collector.collect_all()

    assert total == 2
    mock_datasource.fetch_stats.assert_called_once_with(["v001", "v002"])
    mock_insert.assert_called_once()


@pytest.mark.asyncio
async def test_collect_all_snapshot_at_is_aligned(mock_datasource, mock_session):
    """验证 snapshot_at 被对齐到整点小时。"""
    videos = [make_mock_video(1, "v001")]
    collector = SnapshotCollector(mock_datasource, mock_session)

    captured_rows = []

    with patch.object(collector._video_repo, "get_tracked_videos", new_callable=AsyncMock) as mock_get, \
         patch.object(collector._snapshot_repo, "bulk_insert", new_callable=AsyncMock) as mock_insert:

        mock_get.side_effect = [videos, []]
        mock_insert.side_effect = lambda rows: captured_rows.extend(rows)

        await collector.collect_all()

    assert len(captured_rows) == 1
    snapshot_at = captured_rows[0]["snapshot_at"]
    assert snapshot_at.minute == 0
    assert snapshot_at.second == 0


@pytest.mark.asyncio
async def test_collect_all_empty_tracking_pool(mock_datasource, mock_session):
    """追踪池为空时，不调用 fetch_stats，返回 0。"""
    collector = SnapshotCollector(mock_datasource, mock_session)

    with patch.object(collector._video_repo, "get_tracked_videos", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        total = await collector.collect_all()

    assert total == 0
    mock_datasource.fetch_stats.assert_not_called()


@pytest.mark.asyncio
async def test_collect_all_fetch_stats_exception(mock_datasource, mock_session):
    """fetch_stats 抛出异常时，gracefully 返回 0，不崩溃。"""
    videos = [make_mock_video(1, "v001")]
    mock_datasource.fetch_stats.side_effect = Exception("API 超时")
    collector = SnapshotCollector(mock_datasource, mock_session)

    with patch.object(collector._video_repo, "get_tracked_videos", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [videos, []]
        total = await collector.collect_all()

    assert total == 0


@pytest.mark.asyncio
async def test_collect_batch_filters_unknown_video_ids(mock_datasource, mock_session):
    """fetch_stats 返回了 DB 中不存在的 video_id，应被过滤掉。"""
    videos = [make_mock_video(1, "v001")]  # 只有 v001
    mock_datasource.fetch_stats.return_value = [
        make_mock_stats("v001", 100_000),
        make_mock_stats("v_unknown", 999_999),  # DB 中不存在
    ]
    collector = SnapshotCollector(mock_datasource, mock_session)

    with patch.object(collector._video_repo, "get_tracked_videos", new_callable=AsyncMock) as mock_get, \
         patch.object(collector._snapshot_repo, "bulk_insert", new_callable=AsyncMock) as mock_insert:

        captured_rows = []
        mock_get.side_effect = [videos, []]
        mock_insert.side_effect = lambda rows: captured_rows.extend(rows)

        total = await collector.collect_all()

    # 只有 v001 被写入，v_unknown 被过滤
    assert total == 1
    assert all(r["video_id"] == 1 for r in captured_rows)
