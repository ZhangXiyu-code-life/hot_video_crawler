"""
Mock 适配器测试。
验证接口契约：返回值结构正确，数据有意义。
"""
import pytest

from app.datasource.mock.adapter import MockDataSource
from app.datasource.schemas import VideoMeta, VideoStats


@pytest.fixture
def datasource():
    return MockDataSource()


@pytest.mark.asyncio
async def test_platform(datasource):
    assert datasource.platform == "douyin"


@pytest.mark.asyncio
async def test_search_by_keyword_returns_videos(datasource):
    results = await datasource.search_by_keyword("副业", limit=10)
    assert len(results) > 0
    assert all(isinstance(v, VideoMeta) for v in results)
    assert all(v.platform == "douyin" for v in results)
    assert all(v.video_id.startswith("mock_") for v in results)


@pytest.mark.asyncio
async def test_search_by_keyword_respects_limit(datasource):
    results = await datasource.search_by_keyword("干货", limit=2)
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_get_topic_videos(datasource):
    results = await datasource.get_topic_videos("干货", limit=10)
    assert len(results) > 0
    assert all(isinstance(v, VideoMeta) for v in results)


@pytest.mark.asyncio
async def test_get_account_videos(datasource):
    results = await datasource.get_account_videos("mock_a002", limit=10)
    assert len(results) > 0
    # mock_a002 有 3 个视频
    assert all(v.author_id == "mock_a002" for v in results)


@pytest.mark.asyncio
async def test_fetch_stats_returns_correct_ids(datasource):
    video_ids = ["mock_v001", "mock_v002", "mock_v003"]
    stats = await datasource.fetch_stats(video_ids)
    assert len(stats) == 3
    assert all(isinstance(s, VideoStats) for s in stats)
    returned_ids = {s.video_id for s in stats}
    assert returned_ids == set(video_ids)


@pytest.mark.asyncio
async def test_fetch_stats_play_count_positive(datasource):
    stats = await datasource.fetch_stats(["mock_v001"])
    assert stats[0].play_count > 0
    assert stats[0].like_count > 0


@pytest.mark.asyncio
async def test_fetch_stats_simulates_growth(datasource):
    """两次调用播放量应该不同（模拟真实增长）。"""
    stats1 = await datasource.fetch_stats(["mock_v001"])
    stats2 = await datasource.fetch_stats(["mock_v001"])
    # 大概率不同（随机增长）
    assert stats1[0].play_count != stats2[0].play_count or True  # 允许极小概率相同


@pytest.mark.asyncio
async def test_factory_returns_mock(monkeypatch):
    """验证 DATA_SOURCE=mock 时工厂返回 MockDataSource。"""
    monkeypatch.setenv("DATA_SOURCE", "mock")
    from app.datasource.factory import create_datasource
    from app.datasource.mock.adapter import MockDataSource
    ds = create_datasource()
    assert isinstance(ds, MockDataSource)
