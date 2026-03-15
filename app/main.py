from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.db.session import AsyncSessionLocal, engine
from app.utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 启动 ─────────────────────────────────────────────────────────────────
    logger.info("starting", env=settings.app_env)

    # 检查数据库连通性
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("database connected")

    # 检查 Redis 连通性
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    await redis_client.ping()
    logger.info("redis connected")

    # 将 redis_client 挂到 app.state，供依赖注入使用
    app.state.redis = redis_client

    # 初始化数据源、布隆过滤器、调度器
    from app.datasource.factory import create_datasource
    from app.snapshot.scheduler import build_scheduler
    from app.utils.bloom_filter import BloomFilter

    datasource = create_datasource(redis_client)
    bloom_filter = BloomFilter(redis_client)

    scheduler = build_scheduler(
        datasource=datasource,
        session_factory=AsyncSessionLocal,
        bloom_filter=bloom_filter,
    )
    # 初始化通知 dispatcher
    from app.notification.dispatcher import build_dispatcher
    dispatcher = build_dispatcher()
    app.state.dispatcher = dispatcher

    scheduler = build_scheduler(
        datasource=datasource,
        session_factory=AsyncSessionLocal,
        bloom_filter=bloom_filter,
    )
    scheduler.start()
    app.state.datasource = datasource
    app.state.scheduler = scheduler
    logger.info("scheduler started", jobs=len(scheduler.get_jobs()))

    yield

    # ── 关闭 ─────────────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    await redis_client.aclose()
    await engine.dispose()
    logger.info("shutdown complete")


app = FastAPI(
    title="Hot Video Crawler",
    description="抖音知识卖课赛道热门视频榜单 Agent",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
async def health_check():
    """健康检查：验证 DB + Redis 连通性。"""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    redis_client: aioredis.Redis = app.state.redis
    await redis_client.ping()
    return {"status": "ok", "env": settings.app_env}


from app.api.routers import admin, ranking, tracks, videos

app.include_router(ranking.router, prefix=settings.api_prefix)
app.include_router(videos.router, prefix=settings.api_prefix)
app.include_router(tracks.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
