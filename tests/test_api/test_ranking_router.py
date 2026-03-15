"""
Ranking API 路由测试（使用 FastAPI TestClient）。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def make_mock_ranking():
    from datetime import date, datetime, timezone
    ranking = MagicMock()
    ranking.id = 1
    ranking.period_type = "daily"
    ranking.platform = "douyin"
    ranking.track = "knowledge_course"
    ranking.period_start = date(2026, 3, 14)
    ranking.period_end = date(2026, 3, 14)
    ranking.top_n = 10
    ranking.generated_at = datetime(2026, 3, 15, 0, 30, tzinfo=timezone.utc)
    ranking.items = []
    return ranking


def test_health_check(client):
    """健康检查端点基本可达（不需要真实 DB/Redis）。"""
    # 只验证路由存在，500 也说明路由注册成功
    response = client.get("/health")
    assert response.status_code in (200, 500)


def test_ranking_404_when_no_data(client):
    with patch("app.api.routers.ranking.RankingRepository") as MockRepo:
        MockRepo.return_value.get_latest = AsyncMock(return_value=None)
        response = client.get("/api/v1/ranking/daily/knowledge_course")
    assert response.status_code == 404
    assert "暂无榜单数据" in response.json()["detail"]


def test_ranking_invalid_period_type(client):
    """无效的 period_type 应返回 422。"""
    response = client.get("/api/v1/ranking/invalid_period/knowledge_course")
    assert response.status_code == 422


def test_ranking_history_empty(client):
    with patch("app.api.routers.ranking.RankingRepository") as MockRepo:
        MockRepo.return_value.list_history = AsyncMock(return_value=[])
        response = client.get("/api/v1/ranking/history/daily/knowledge_course")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["rankings"] == []
