"""
补录快照脚本。

对数据库中已有的所有视频，在过去 7 天的整点时刻（每天 00:00 和 12:00）
插入模拟快照数据，为增量计算提供历史基线。

用法：
    python scripts/backfill_snapshots.py [--days 7]
"""
import asyncio
import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.models.snapshot import VideoSnapshot
from app.db.models.video import Video
from app.db.session import AsyncSessionLocal


async def backfill(days: int = 7) -> None:
    now = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)

    # 生成补录时间点：过去 days 天，每天 00:00 和 12:00 UTC
    time_points: list[datetime] = []
    for d in range(days, 0, -1):
        base = now - timedelta(days=d)
        for hour in (0, 12):
            time_points.append(base.replace(hour=hour))

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video.id))
        video_ids = [row[0] for row in result.all()]

        if not video_ids:
            print("数据库中没有视频，请先运行发现任务或初始化 seed 数据。")
            return

        print(f"找到 {len(video_ids)} 个视频，补录 {len(time_points)} 个时间点…")

        inserted = 0
        for video_id in video_ids:
            # 模拟起始播放数（基准值）
            base_plays = random.randint(50_000, 500_000)
            base_likes = int(base_plays * random.uniform(0.03, 0.08))
            base_comments = int(base_plays * random.uniform(0.005, 0.02))
            base_shares = int(base_plays * random.uniform(0.01, 0.04))

            for i, ts in enumerate(time_points):
                # 每个时间点叠加随机增量
                plays = base_plays + i * random.randint(500, 5000)
                likes = base_likes + i * random.randint(10, 200)
                comments = base_comments + i * random.randint(2, 50)
                shares = base_shares + i * random.randint(5, 100)

                stmt = (
                    insert(VideoSnapshot)
                    .values(
                        video_id=video_id,
                        play_count=plays,
                        like_count=likes,
                        comment_count=comments,
                        share_count=shares,
                        collect_count=0,
                        snapshot_at=ts,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["video_id", "snapshot_at"]
                    )
                )
                await session.execute(stmt)
                inserted += 1

        await session.commit()
        print(f"补录完成，共插入 {inserted} 条快照记录。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="补录历史快照数据")
    parser.add_argument("--days", type=int, default=7, help="补录天数（默认 7）")
    args = parser.parse_args()
    asyncio.run(backfill(args.days))
