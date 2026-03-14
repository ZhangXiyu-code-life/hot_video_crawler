"""
VideoDiscoveryEngine：视频发现引擎。

编排三路发现策略 → 去重 → 赛道分类 → 写入追踪池。
每次运行扩充一批新的待追踪视频。
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.classifier.account_tag_rule import AccountTagClassifier
from app.classifier.engine import TrackClassifier
from app.classifier.keyword_rule import KeywordRuleClassifier
from app.classifier.llm_classifier import LLMClassifier
from app.config import get_settings
from app.datasource.base import PlatformDataSource
from app.datasource.schemas import VideoMeta
from app.db.models.account import AccountWhitelist
from app.db.repositories.video_repo import VideoRepository
from app.discovery.deduplicator import VideoDeduplicator
from app.discovery.strategies.account_strategy import AccountStrategy
from app.discovery.strategies.keyword_strategy import KeywordStrategy
from app.discovery.strategies.topic_strategy import TopicStrategy
from app.utils.bloom_filter import BloomFilter
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class VideoDiscoveryEngine:

    def __init__(
        self,
        datasource: PlatformDataSource,
        session: AsyncSession,
        bloom_filter: BloomFilter,
    ) -> None:
        self._datasource = datasource
        self._session = session
        self._bloom = bloom_filter
        self._video_repo = VideoRepository(session)

    async def run(self, track_name: str) -> int:
        """
        对指定赛道执行一次完整的发现流程。
        返回本次新入库的视频数量。
        """
        logger.info("discovery_start", track=track_name)

        # 初始化分类器
        classifier = await self._build_classifier(track_name)
        deduplicator = VideoDeduplicator(self._bloom)

        # 获取赛道配置
        track_cfg = self._get_track_config(track_name)

        # 并发运行三路策略
        account_strategy = AccountStrategy(self._session)
        keyword_strategy = KeywordStrategy()
        topic_strategy = TopicStrategy()

        results = await asyncio.gather(
            account_strategy.run(self._datasource, track_name, track_cfg),
            keyword_strategy.run(self._datasource, track_name, track_cfg),
            topic_strategy.run(self._datasource, track_name, track_cfg),
            return_exceptions=True,
        )

        # 合并三路结果，忽略异常的那路
        all_videos: list[VideoMeta] = []
        strategy_names = ["account", "keyword", "topic"]
        for name, result in zip(strategy_names, results):
            if isinstance(result, Exception):
                logger.error("strategy_failed", strategy=name, error=str(result))
            else:
                all_videos.extend(result)

        logger.info("discovery_merged", track=track_name, total=len(all_videos))

        # 去重
        new_videos = await deduplicator.filter_new(all_videos)

        # 分类过滤 + 入库
        saved = 0
        for video in new_videos:
            result = await classifier.classify(video, track_name)
            if not result.is_match:
                continue

            await self._video_repo.upsert(
                platform=video.platform,
                video_id=video.video_id,
                track=track_name,
                title=video.title,
                author_id=video.author_id,
                author_name=video.author_name,
                cover_url=video.cover_url,
                video_url=video.video_url,
                published_at=video.published_at,
                track_confidence=result.confidence,
                classify_stage=result.stage,
                discovery_source="account" if video.author_id else "keyword",
                is_tracking=True,
            )
            saved += 1

        await self._session.commit()
        logger.info("discovery_done", track=track_name, saved=saved)
        return saved

    async def _build_classifier(self, track_name: str) -> TrackClassifier:
        """构建分类器，加载账号白名单构建 account_tag_map。"""
        # 加载账号白名单构建 {account_id: track_name} 映射
        stmt = select(AccountWhitelist).where(
            AccountWhitelist.is_active.is_(True),
            AccountWhitelist.platform == self._datasource.platform,
        )
        result = await self._session.execute(stmt)
        accounts = result.scalars().all()
        account_track_map = {acc.account_id: acc.track for acc in accounts}

        keyword_clf = KeywordRuleClassifier(settings.keywords_config)
        account_clf = AccountTagClassifier(account_track_map)
        llm_clf = LLMClassifier()

        return TrackClassifier(
            keyword_classifier=keyword_clf,
            account_classifier=account_clf,
            llm_classifier=llm_clf,
            tracks_config=settings.tracks_config,
        )

    def _get_track_config(self, track_name: str) -> dict:
        for track in settings.tracks_config.get("tracks", []):
            if track["name"] == track_name:
                return track
        return {}
