from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine
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

    # TODO Phase 4: 在此启动 APScheduler
    # from app.snapshot.scheduler import start_scheduler
    # scheduler = start_scheduler()
    # app.state.scheduler = scheduler

    yield

    # ── 关闭 ─────────────────────────────────────────────────────────────────
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


# TODO Phase 6: 注册业务路由
# from app.api.routers import ranking, videos, tracks, admin
# app.include_router(ranking.router, prefix=settings.api_prefix)
# app.include_router(videos.router, prefix=settings.api_prefix)
# app.include_router(tracks.router, prefix=settings.api_prefix)
# app.include_router(admin.router, prefix=settings.api_prefix)
