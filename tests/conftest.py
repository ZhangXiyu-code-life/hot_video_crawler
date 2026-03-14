import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
import app.db.models  # noqa: F401 确保所有 Model 被注册

TEST_DATABASE_URL = "postgresql+asyncpg://hvc:hvcpassword@localhost:5433/hot_video_crawler_test"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """每个测试用例使用独立事务，测试完毕回滚，保证隔离性。"""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()
