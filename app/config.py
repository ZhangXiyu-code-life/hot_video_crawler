from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── 数据库 ────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://hvc:hvcpassword@localhost:5432/hot_video_crawler"
    )

    # ── Redis ─────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── 数据源 ────────────────────────────────────────
    data_source: Literal["feigua", "chanmama", "crawler"] = "feigua"
    feigua_api_key: str = ""
    feigua_base_url: str = "https://api.feigua.cn"
    chanmama_api_key: str = ""
    chanmama_base_url: str = "https://api.chanmama.com"

    # ── LLM ──────────────────────────────────────────
    claude_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"

    # ── 通知 ──────────────────────────────────────────
    feishu_webhook_url: str = ""
    email_smtp_host: str = ""
    email_smtp_port: int = 465
    email_smtp_user: str = ""
    email_smtp_password: str = ""
    email_to: str = ""

    # ── 应用 ──────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # ── 采集参数 ──────────────────────────────────────
    snapshot_batch_size: int = 100       # 每批快照采集视频数
    discovery_interval_hours: int = 6    # 发现任务间隔（小时）
    classifier_llm_threshold: float = 0.8  # 低于此置信度触发 LLM 分类

    @property
    def tracks_config(self) -> dict:
        return _load_yaml(CONFIG_DIR / "tracks.yaml")

    @property
    def keywords_config(self) -> dict:
        return _load_yaml(CONFIG_DIR / "keywords.yaml")

    @property
    def seed_accounts_config(self) -> list:
        return _load_yaml(CONFIG_DIR / "seed_accounts.yaml")


def _load_yaml(path: Path) -> dict | list:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
