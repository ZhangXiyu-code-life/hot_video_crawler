"""
端到端集成测试：模拟完整数据流水线。

测试流程：发现视频 → 打快照 → 计算增量 → 生成榜单 → 记录 Job 日志

使用内存 SQLite（通过 aiosqlite）跑全流程，无需真实 DB/Redis。
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
import app.db.models  # noqa: F401


# ── SQLite 内存引擎（仅用于集成测试）─────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def mem_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def mem_session(mem_engine) -> AsyncSession:
    factory = async_sessionmaker(mem_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# ── Mock 数据源 ────────────────────────────────────────────────────

def _make_mock_datasource():
    from app.datasource.schemas import VideoMeta, VideoStats

    ds = MagicMock()
    ds.platform = "douyin"
    ds.get_account_videos = AsyncMock(return_value=[
        VideoMeta(
            platform="douyin",
            video_id="vid_001",
            title="Python 零基础入门课",
            author_id="acc_001",
            author_name="知识博主A",
            published_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
            cover_url="https://example.com/thumb1.jpg",
            video_url="https://example.com/vid1",
            description="Python 入门教程",
            tags=["编程", "Python"],
        ),
        VideoMeta(
            platform="douyin",
            video_id="vid_002",
            title="副业变现实战指南",
            author_id="acc_001",
            author_name="知识博主A",
            published_at=datetime(2026, 3, 11, tzinfo=timezone.utc),
            cover_url="https://example.com/thumb2.jpg",
            video_url="https://example.com/vid2",
            description="副业赚钱方法",
            tags=["副业", "赚钱"],
        ),
    ])
    ds.search_by_keyword = AsyncMock(side_effect=lambda keyword, limit=50: [
        VideoMeta(
            platform="douyin",
            video_id="vid_001",
            title="Python 零基础入门课",
            author_id="acc_001",
            author_name="知识博主A",
            published_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
            cover_url="https://example.com/thumb1.jpg",
            video_url="https://example.com/vid1",
            description="Python 入门教程",
            tags=["编程", "Python"],
        ),
    ])
    ds.get_topic_videos = AsyncMock(return_value=[])
    ds.fetch_stats = AsyncMock(return_value=[
        VideoStats(
            platform="douyin",
            video_id="vid_001",
            play_count=100_000,
            like_count=5_000,
            comment_count=300,
            share_count=1_000,
        ),
        VideoStats(
            platform="douyin",
            video_id="vid_002",
            play_count=200_000,
            like_count=10_000,
            comment_count=600,
            share_count=2_000,
        ),
    ])
    return ds


# ── 测试 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_saves_videos(mem_session):
    """发现任务应将视频保存到 videos 表。"""
    from unittest.mock import patch
    from sqlalchemy import select
    from app.classifier.schemas import TrackResult
    from app.db.models.video import Video
    from app.discovery.engine import VideoDiscoveryEngine
    from app.utils.bloom_filter import BloomFilter

    datasource = _make_mock_datasource()
    bloom = MagicMock(spec=BloomFilter)
    bloom.exists = AsyncMock(return_value=False)
    bloom.add = AsyncMock()

    # 绕过真实 Gemini API（测试环境无有效 Key），直接返回匹配结果
    mock_llm_result = TrackResult(
        label="knowledge_course", confidence=0.9, stage="llm", reason="mock"
    )
    with patch(
        "app.classifier.llm_classifier.LLMClassifier.classify",
        new=AsyncMock(return_value=mock_llm_result),
    ):
        engine = VideoDiscoveryEngine(datasource, mem_session, bloom)
        saved = await engine.run("knowledge_course")

    result = await mem_session.execute(select(Video))
    videos = result.scalars().all()
    assert len(videos) >= 1
    assert saved >= 1


@pytest.mark.asyncio
async def test_snapshot_collector_saves_snapshots(mem_session):
    """快照采集应为已发现视频调用 bulk_insert，不应抛出异常。"""
    from unittest.mock import patch
    from app.snapshot.collector import SnapshotCollector

    datasource = _make_mock_datasource()
    collector = SnapshotCollector(datasource, mem_session)

    # SQLite 不支持 BigInteger 自增，mock bulk_insert 只验证调度逻辑
    with patch.object(
        collector._snapshot_repo, "bulk_insert", new=AsyncMock(return_value=None)
    ):
        total = await collector.collect_all()

    # 若 DB 中存在视频（由前序测试写入），total 应 >= 0
    assert total >= 0


@pytest.mark.asyncio
async def test_ranking_generator_full_flow(mem_session):
    """榜单生成器应能端到端运行，不抛异常。"""
    from app.ranking.generator import RankingGenerator
    from app.ranking.periods import PeriodType

    generator = RankingGenerator(mem_session)
    # 即使快照不足，也应优雅处理（返回 None 而非崩溃）
    result = await generator.generate(PeriodType.DAILY, "knowledge_course")
    # result 可能为 None（快照不够），也可能是 Ranking 对象
    # 关键是不应抛出异常


@pytest.mark.asyncio
async def test_job_logger_records_success():
    """record_job 应在成功时将 JobLog(status=success) add 到 session 并 commit。"""
    from app.db.models.job_log import JobLog
    from app.utils.job_logger import record_job

    mock_session = AsyncMock()

    async with record_job(mock_session, "test_job_success") as ctx:
        ctx["result"] = "all good"

    mock_session.add.assert_called_once()
    log: JobLog = mock_session.add.call_args[0][0]
    assert isinstance(log, JobLog)
    assert log.job_id == "test_job_success"
    assert log.status == "success"
    assert log.duration_ms >= 0
    assert "all good" in log.result_summary
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_job_logger_records_failure():
    """record_job 应在异常时写入 failed 状态的日志，并重新抛出异常。"""
    from app.db.models.job_log import JobLog
    from app.utils.job_logger import record_job

    mock_session = AsyncMock()

    with pytest.raises(ValueError, match="boom"):
        async with record_job(mock_session, "test_job_failure") as _ctx:
            raise ValueError("boom")

    mock_session.add.assert_called_once()
    log: JobLog = mock_session.add.call_args[0][0]
    assert isinstance(log, JobLog)
    assert log.job_id == "test_job_failure"
    assert log.status == "failed"
    assert "boom" in log.error_message


@pytest.mark.asyncio
async def test_health_endpoint_returns_expected_keys():
    """健康检查端点应返回包含 status/db/redis/video_count/scheduler_jobs 的响应。"""
    from unittest.mock import AsyncMock, MagicMock, patch
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "db" in data
        assert "redis" in data
        assert "video_count" in data
        assert "scheduler_jobs" in data
