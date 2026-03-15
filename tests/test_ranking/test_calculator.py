"""
IncrementCalculator 单元测试。
核心：增量计算的正确性、边界条件处理。
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ranking.calculator import IncrementCalculator


def make_snapshot(snap_id: int, play_count: int) -> MagicMock:
    s = MagicMock()
    s.id = snap_id
    s.play_count = play_count
    return s


T_START = datetime(2026, 3, 13, 0, 0, 0, tzinfo=timezone.utc)
T_END = datetime(2026, 3, 14, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def calculator(mock_session):
    return IncrementCalculator(mock_session)


@pytest.mark.asyncio
async def test_normal_increment(calculator):
    """正常增量：期末 - 期初 = 5000。"""
    calculator._repo.get_snapshot_at = AsyncMock(
        side_effect=[
            make_snapshot(1, 10_000),   # 期初
            make_snapshot(2, 15_000),   # 期末
        ]
    )
    result = await calculator.calc(1, T_START, T_END)
    assert result == 5_000


@pytest.mark.asyncio
async def test_no_start_snapshot_returns_zero(calculator):
    """期初无快照 → 返回 0。"""
    calculator._repo.get_snapshot_at = AsyncMock(
        side_effect=[None, make_snapshot(2, 15_000)]
    )
    result = await calculator.calc(1, T_START, T_END)
    assert result == 0


@pytest.mark.asyncio
async def test_no_end_snapshot_returns_zero(calculator):
    """期末无快照 → 返回 0。"""
    calculator._repo.get_snapshot_at = AsyncMock(
        side_effect=[make_snapshot(1, 10_000), None]
    )
    result = await calculator.calc(1, T_START, T_END)
    assert result == 0


@pytest.mark.asyncio
async def test_negative_delta_returns_zero(calculator):
    """播放量回撤（平台修正数据）→ 返回 0，不产生负数增量。"""
    calculator._repo.get_snapshot_at = AsyncMock(
        side_effect=[
            make_snapshot(1, 15_000),   # 期初反而更大
            make_snapshot(2, 10_000),   # 期末更小
        ]
    )
    result = await calculator.calc(1, T_START, T_END)
    assert result == 0


@pytest.mark.asyncio
async def test_same_snapshot_returns_zero(calculator):
    """期初期末是同一条快照（视频追踪时间不足）→ 返回 0。"""
    snap = make_snapshot(1, 10_000)
    calculator._repo.get_snapshot_at = AsyncMock(return_value=snap)
    result = await calculator.calc(1, T_START, T_END)
    assert result == 0


@pytest.mark.asyncio
async def test_calc_batch_returns_all_ids(calculator):
    """批量计算返回所有视频的增量字典。"""
    calculator._repo.get_snapshot_at = AsyncMock(
        side_effect=[
            make_snapshot(1, 10_000), make_snapshot(2, 15_000),  # video 1
            make_snapshot(3, 20_000), make_snapshot(4, 25_000),  # video 2
            make_snapshot(5, 30_000), make_snapshot(6, 35_000),  # video 3
        ]
    )
    result = await calculator.calc_batch([1, 2, 3], T_START, T_END)
    assert set(result.keys()) == {1, 2, 3}
    assert result[1] == 5_000
    assert result[2] == 5_000
    assert result[3] == 5_000


@pytest.mark.asyncio
async def test_calc_batch_empty_list(calculator):
    """空列表 → 返回空字典。"""
    result = await calculator.calc_batch([], T_START, T_END)
    assert result == {}
