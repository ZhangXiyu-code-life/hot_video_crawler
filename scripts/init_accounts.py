"""
从 config/seed_accounts.yaml 导入账号白名单到数据库。
幂等执行，重复运行只更新不重复插入。

使用方法：
    python scripts/init_accounts.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.db.models.account import AccountWhitelist
from app.db.session import AsyncSessionLocal

settings = get_settings()


async def main() -> None:
    accounts = settings.seed_accounts_config
    if not accounts:
        accounts = []

    account_list = accounts if isinstance(accounts, list) else accounts.get("accounts", [])

    if not account_list:
        print("seed_accounts.yaml 中无账号配置，退出。")
        return

    async with AsyncSessionLocal() as session:
        for acc in account_list:
            stmt = (
                insert(AccountWhitelist)
                .values(
                    platform=acc["platform"],
                    account_id=acc["account_id"],
                    account_name=acc.get("account_name", ""),
                    track=acc["track"],
                    is_active=True,
                    source="manual",
                )
                .on_conflict_do_update(
                    index_elements=["platform", "account_id"],
                    set_={
                        "account_name": acc.get("account_name", ""),
                        "track": acc["track"],
                        "is_active": True,
                    },
                )
            )
            await session.execute(stmt)
            print(f"  ✓ 账号已同步：{acc['account_name']} ({acc['platform']}:{acc['account_id']})")

        await session.commit()
    print(f"\n完成，共同步 {len(account_list)} 个账号。")


if __name__ == "__main__":
    asyncio.run(main())
