"""
RankingGenerator 单元测试。
验证榜单排序、Top N 截断、空数据处理。
"""
from datetime import timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ranking.generator import RankingGenerator
from app.ranking.periods import PeriodType


def make_video(db_id: int, title: str, author: str = "测试作者"):
    v = MagicMock()
    v.id = db_id
    v.video_id = f"platform_v{db_id}"
    v.title = title
    v.author_name = author
    v.cover_url = None
    return v


def make_snapshot(play_count: int):
    s = MagicMock()
    s.play_count = play_count
    return s


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def generator(mock_session):
    return RankingGenerator(mock_session)


@pytest.mark.asyncio
async def test_generate_daily_ranking_correct_order(generator):
    """日榜：按增量降序排列，第一名增量最大。"""
    videos = [
        make_video(1, "视频A"),
        make_video(2, "视频B"),
        make_video(3, "视频C"),
    ]
    increment_map = {1: 5_000, 2: 20_000, 3: 10_000}

    captured_items = []

    with patch.object(generator._video_repo, "get_tracked_videos", new_callable=AsyncMock, return_value=videos), \
         patch.object(generator._calculator, "calc_batch", new_callable=AsyncMock, return_value=increment_map), \
         patch.object(generator._ranking_repo, "upsert_ranking", new_callable=AsyncMock, return_value=MagicMock(id=1)), \
         patch.object(generator._ranking_repo, "replace_items", new_callable=AsyncMock) as mock_replace, \
         patch.object(generator._session, "commit", new_callable=AsyncMock), \
         patch("app.ranking.generator.SnapshotRepository") as MockSnapRepo:

        MockSnapRepo.return_value.get_snapshot_at = AsyncMock(return_value=make_snapshot(50_000))
        mock_replace.side_effect = lambda rid, items: captured_items.extend(items)

        await generator.generate(PeriodType.DAILY, "knowledge_course")

    assert len(captured_items) == 3
    # 第一名应是增量最大的视频B（20000）
    assert captured_items[0]["rank"] == 1
    assert captured_items[0]["play_increment"] == 20_000
    assert captured_items[0]["video_title"] == "视频B"
    # 严格降序
    increments = [item["play_increment"] for item in captured_items]
    assert increments == sorted(increments, reverse=True)


@pytest.mark.asyncio
async def test_generate_monthly_top_n_is_20(generator):
    """月榜 Top N = 20，超过 20 条视频时只保留前 20。"""
    videos = [make_video(i, f"视频{i}") for i in range(1, 31)]  # 30 条
    increment_map = {i: i * 1000 for i in range(1, 31)}

    with patch.object(generator._video_repo, "get_tracked_videos", new_callable=AsyncMock, return_value=videos), \
         patch.object(generator._calculator, "calc_batch", new_callable=AsyncMock, return_value=increment_map), \
         patch.object(generator._ranking_repo, "upsert_ranking", new_callable=AsyncMock, return_value=MagicMock(id=1)), \
         patch.object(generator._ranking_repo, "replace_items", new_callable=AsyncMock) as mock_replace, \
         patch.object(generator._session, "commit", new_callable=AsyncMock), \
         patch("app.ranking.generator.SnapshotRepository") as MockSnapRepo:

        MockSnapRepo.return_value.get_snapshot_at = AsyncMock(return_value=make_snapshot(100_000))
        captured = []
        mock_replace.side_effect = lambda rid, items: captured.extend(items)

        await generator.generate(PeriodType.MONTHLY, "knowledge_course")

    assert len(captured) == 20


@pytest.mark.asyncio
async def test_generate_all_zero_increments_skips(generator):
    """所有视频增量为 0 时，不写入 DB，直接跳过。"""
    videos = [make_video(1, "视频A"), make_video(2, "视频B")]
    increment_map = {1: 0, 2: 0}

    with patch.object(generator._video_repo, "get_tracked_videos", new_callable=AsyncMock, return_value=videos), \
         patch.object(generator._calculator, "calc_batch", new_callable=AsyncMock, return_value=increment_map), \
         patch.object(generator._ranking_repo, "upsert_ranking", new_callable=AsyncMock) as mock_upsert, \
         patch.object(generator._session, "commit", new_callable=AsyncMock):

        await generator.generate(PeriodType.DAILY, "knowledge_course")

    mock_upsert.assert_not_called()


@pytest.mark.asyncio
async def test_generate_no_videos_skips(generator):
    """追踪池为空时，不写入 DB。"""
    with patch.object(generator._video_repo, "get_tracked_videos", new_callable=AsyncMock, return_value=[]), \
         patch.object(generator._ranking_repo, "upsert_ranking", new_callable=AsyncMock) as mock_upsert:

        await generator.generate(PeriodType.DAILY, "knowledge_course")

    mock_upsert.assert_not_called()


@pytest.mark.asyncio
async def test_ranking_items_have_correct_rank_sequence(generator):
    """榜单条目的 rank 字段从 1 开始连续递增。"""
    videos = [make_video(i, f"视频{i}") for i in range(1, 6)]
    increment_map = {i: (6 - i) * 1000 for i in range(1, 6)}

    captured = []

    with patch.object(generator._video_repo, "get_tracked_videos", new_callable=AsyncMock, return_value=videos), \
         patch.object(generator._calculator, "calc_batch", new_callable=AsyncMock, return_value=increment_map), \
         patch.object(generator._ranking_repo, "upsert_ranking", new_callable=AsyncMock, return_value=MagicMock(id=1)), \
         patch.object(generator._ranking_repo, "replace_items", new_callable=AsyncMock) as mock_replace, \
         patch.object(generator._session, "commit", new_callable=AsyncMock), \
         patch("app.ranking.generator.SnapshotRepository") as MockSnapRepo:

        MockSnapRepo.return_value.get_snapshot_at = AsyncMock(return_value=make_snapshot(50_000))
        mock_replace.side_effect = lambda rid, items: captured.extend(items)

        await generator.generate(PeriodType.WEEKLY, "knowledge_course")

    ranks = [item["rank"] for item in captured]
    assert ranks == list(range(1, len(captured) + 1))
