"""
从 config/tracks.yaml 初始化赛道配置到数据库。
支持幂等执行（重复运行只会更新，不会重复插入）。

使用方法：
    python scripts/init_tracks.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.db.models.track import Track
from app.db.session import AsyncSessionLocal

settings = get_settings()


async def main() -> None:
    tracks_config = settings.tracks_config
    tracks = tracks_config.get("tracks", [])

    if not tracks:
        print("tracks.yaml 中无赛道配置，退出。")
        return

    async with AsyncSessionLocal() as session:
        for track_cfg in tracks:
            stmt = (
                insert(Track)
                .values(
                    name=track_cfg["name"],
                    display_name=track_cfg["display_name"],
                    description=track_cfg.get("description", ""),
                    keywords_json=json.dumps(
                        track_cfg.get("keywords", []), ensure_ascii=False
                    ),
                    topic_tags_json=json.dumps(
                        track_cfg.get("topic_tags", []), ensure_ascii=False
                    ),
                    llm_prompt=track_cfg.get("llm_prompt", ""),
                    is_active=True,
                )
                .on_conflict_do_update(
                    index_elements=["name"],
                    set_={
                        "display_name": track_cfg["display_name"],
                        "description": track_cfg.get("description", ""),
                        "keywords_json": json.dumps(track_cfg.get("keywords", []), ensure_ascii=False),
                        "topic_tags_json": json.dumps(track_cfg.get("topic_tags", []), ensure_ascii=False),
                        "llm_prompt": track_cfg.get("llm_prompt", ""),
                    },
                )
            )
            await session.execute(stmt)
            print(f"  ✓ 赛道已同步：{track_cfg['name']} ({track_cfg['display_name']})")

        await session.commit()
    print(f"\n完成，共同步 {len(tracks)} 个赛道。")


if __name__ == "__main__":
    asyncio.run(main())
