"""
TrackClassifier：三阶分类流水线。

Stage1: 关键词规则（快，覆盖 ~60%）
Stage2: 账号标签（中，覆盖白名单账号视频）
Stage3: Gemini LLM（慢，兜底剩余 ~20%）

只有前两阶段置信度 < threshold 时才调用 LLM，控制成本。
"""
from app.classifier.account_tag_rule import AccountTagClassifier
from app.classifier.keyword_rule import KeywordRuleClassifier
from app.classifier.llm_classifier import LLMClassifier
from app.classifier.schemas import TrackResult
from app.config import get_settings
from app.datasource.schemas import VideoMeta
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TrackClassifier:

    def __init__(
        self,
        keyword_classifier: KeywordRuleClassifier,
        account_classifier: AccountTagClassifier,
        llm_classifier: LLMClassifier,
        tracks_config: dict,
    ) -> None:
        self._keyword = keyword_classifier
        self._account = account_classifier
        self._llm = llm_classifier
        self._tracks_config = tracks_config        # 来自 tracks.yaml
        self._threshold = settings.classifier_llm_threshold

    async def classify(self, video: VideoMeta, track_name: str) -> TrackResult:
        """
        对单个视频执行三阶分类，返回最终 TrackResult。
        """
        best_pre_llm: TrackResult | None = None  # 保留 Stage1/2 最佳结果，LLM 失败时降级使用

        # Stage1: 关键词规则
        result = self._keyword.classify(video, track_name)
        if result:
            best_pre_llm = result
            if result.confidence >= self._threshold:
                logger.debug("classified_by_rule", video_id=video.video_id, conf=result.confidence)
                return result

        # Stage2: 账号标签
        result = self._account.classify(video, track_name)
        if result:
            if not best_pre_llm or result.confidence > best_pre_llm.confidence:
                best_pre_llm = result
            if result.confidence >= self._threshold:
                logger.debug("classified_by_tag", video_id=video.video_id, conf=result.confidence)
                return result

        # Stage3: LLM 兜底
        track_cfg = self._get_track_config(track_name)
        prompt_template = track_cfg.get("llm_prompt", "")
        if not prompt_template:
            return best_pre_llm or TrackResult(label="other", confidence=0.0, stage="rule")

        logger.debug("calling_llm_classifier", video_id=video.video_id, track=track_name)
        llm_result = await self._llm.classify(video, track_name, prompt_template)

        # LLM 无 Key 或调用失败时（confidence=0），降级使用 Stage1/2 最佳结果
        if llm_result.confidence == 0.0 and best_pre_llm is not None:
            logger.debug(
                "llm_fallback_to_pre_stage",
                video_id=video.video_id,
                fallback_conf=best_pre_llm.confidence,
            )
            return best_pre_llm

        return llm_result

    def _get_track_config(self, track_name: str) -> dict:
        """从 tracks.yaml 中找到指定赛道的配置。"""
        for track in self._tracks_config.get("tracks", []):
            if track["name"] == track_name:
                return track
        return {}
