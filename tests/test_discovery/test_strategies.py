import pytest

from app.datasource.mock.adapter import MockDataSource
from app.discovery.strategies.keyword_strategy import KeywordStrategy
from app.discovery.strategies.topic_strategy import TopicStrategy

TRACK_CONFIG = {
    "keywords": ["知识付费", "副业", "干货"],
    "topic_tags": ["干货", "副业"],
}


@pytest.fixture
def datasource():
    return MockDataSource()


@pytest.mark.asyncio
async def test_keyword_strategy_returns_videos(datasource):
    strategy = KeywordStrategy()
    videos = await strategy.run(datasource, "knowledge_course", TRACK_CONFIG)
    assert len(videos) > 0
    assert strategy.name == "keyword"


@pytest.mark.asyncio
async def test_keyword_strategy_empty_keywords(datasource):
    strategy = KeywordStrategy()
    videos = await strategy.run(datasource, "knowledge_course", {})
    assert videos == []


@pytest.mark.asyncio
async def test_topic_strategy_returns_videos(datasource):
    strategy = TopicStrategy()
    videos = await strategy.run(datasource, "knowledge_course", TRACK_CONFIG)
    assert len(videos) > 0
    assert strategy.name == "topic"


@pytest.mark.asyncio
async def test_topic_strategy_empty_tags(datasource):
    strategy = TopicStrategy()
    videos = await strategy.run(datasource, "knowledge_course", {})
    assert videos == []
