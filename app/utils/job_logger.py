"""
Job 执行日志工具。
在 scheduler 的每个 Job 函数中调用，记录执行结果到 job_logs 表。
"""
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job_log import JobLog
from app.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def record_job(session: AsyncSession, job_id: str):
    """
    异步上下文管理器，自动记录 Job 执行时间和结果。

    用法：
        async with record_job(session, "snapshot_am") as ctx:
            total = await collector.collect_all()
            ctx["snapshots"] = total
    """
    started_at = datetime.now(tz=timezone.utc)
    start_ts = time.monotonic()
    summary: dict = {}
    error_msg: str | None = None
    status = "success"

    try:
        yield summary
    except Exception as e:
        status = "failed"
        error_msg = str(e)
        logger.error("job_failed", job_id=job_id, error=error_msg)
        raise
    finally:
        duration_ms = int((time.monotonic() - start_ts) * 1000)
        log = JobLog(
            job_id=job_id,
            status=status,
            duration_ms=duration_ms,
            result_summary=json.dumps(summary, ensure_ascii=False),
            error_message=error_msg,
            started_at=started_at,
            finished_at=datetime.now(tz=timezone.utc),
        )
        session.add(log)
        try:
            await session.commit()
        except Exception:
            pass  # 日志写入失败不影响主流程
