from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.video import AddAccountRequest
from app.db.models.account import AccountWhitelist
from app.ranking.periods import PeriodType

router = APIRouter(prefix="/admin", tags=["管理"])


@router.post("/trigger-discovery")
async def trigger_discovery(request: Request, db: AsyncSession = Depends(get_db)):
    """手动触发一次视频发现任务（所有活跃赛道）。"""
    from app.config import get_settings
    from app.discovery.engine import VideoDiscoveryEngine
    from app.utils.bloom_filter import BloomFilter

    settings = get_settings()
    redis_client = request.app.state.redis
    datasource = request.app.state.datasource
    bloom = BloomFilter(redis_client)

    tracks = [
        t["name"] for t in settings.tracks_config.get("tracks", [])
        if t.get("is_active", True)
    ]
    results = {}
    for track_name in tracks:
        engine = VideoDiscoveryEngine(datasource, db, bloom)
        saved = await engine.run(track_name)
        results[track_name] = saved

    return {"status": "ok", "saved": results}


@router.post("/trigger-snapshot")
async def trigger_snapshot(request: Request, db: AsyncSession = Depends(get_db)):
    """手动触发一次快照采集（全量）。"""
    from app.snapshot.collector import SnapshotCollector

    datasource = request.app.state.datasource
    collector = SnapshotCollector(datasource, db)
    total = await collector.collect_all()
    return {"status": "ok", "snapshots_saved": total}


@router.post("/trigger-ranking/{period_type}")
async def trigger_ranking(
    period_type: PeriodType,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """手动触发指定周期的榜单生成（所有活跃赛道）。"""
    from app.config import get_settings
    from app.notification.dispatcher import build_dispatcher
    from app.ranking.generator import RankingGenerator

    settings = get_settings()
    dispatcher = build_dispatcher()
    generator = RankingGenerator(db, dispatcher)

    tracks = [
        t["name"] for t in settings.tracks_config.get("tracks", [])
        if t.get("is_active", True)
    ]
    for track_name in tracks:
        await generator.generate(period_type, track_name)

    return {"status": "ok", "period": period_type.value, "tracks": tracks}


@router.post("/accounts", status_code=201)
async def add_account(
    body: AddAccountRequest,
    db: AsyncSession = Depends(get_db),
):
    """添加账号到白名单。"""
    stmt = (
        insert(AccountWhitelist)
        .values(
            platform=body.platform,
            account_id=body.account_id,
            account_name=body.account_name,
            track=body.track,
            is_active=True,
            source="manual",
        )
        .on_conflict_do_update(
            index_elements=["platform", "account_id"],
            set_={"account_name": body.account_name, "track": body.track, "is_active": True},
        )
    )
    await db.execute(stmt)
    return {"status": "ok", "account_id": body.account_id}


@router.delete("/accounts/{account_id}")
async def remove_account(
    account_id: str,
    platform: str = "douyin",
    db: AsyncSession = Depends(get_db),
):
    """将账号从白名单中停用。"""
    from sqlalchemy import update
    stmt = (
        update(AccountWhitelist)
        .where(
            AccountWhitelist.account_id == account_id,
            AccountWhitelist.platform == platform,
        )
        .values(is_active=False)
    )
    await db.execute(stmt)
    return {"status": "ok", "account_id": account_id}
