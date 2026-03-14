"""
Stage3：Gemini LLM 分类器（兜底）。
仅在前两阶段置信度 < 阈值时触发，控制 API 成本。
"""
import json

from app.classifier.schemas import TrackResult
from app.config import get_settings
from app.datasource.schemas import VideoMeta
from app.utils.logging import get_logger
from app.utils.retry import with_retry

logger = get_logger(__name__)
settings = get_settings()


class LLMClassifier:

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        """懒加载 Gemini 客户端，避免无 API Key 时启动报错。"""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._client = genai.GenerativeModel(settings.gemini_model)
        return self._client

    @with_retry(max_attempts=3, min_wait=2.0, max_wait=10.0)
    async def classify(
        self,
        video: VideoMeta,
        track_name: str,
        prompt_template: str,
    ) -> TrackResult:
        """
        调用 Gemini API 判断视频是否属于目标赛道。
        prompt_template 来自 tracks.yaml 中的 llm_prompt 字段。
        """
        if not settings.gemini_api_key:
            logger.warning("llm_classifier_no_api_key", track=track_name)
            return TrackResult(label="other", confidence=0.0, stage="llm", reason="无 API Key")

        prompt = prompt_template.format(
            title=video.title,
            description=video.description or "",
            author_bio=video.author_bio or "",
        )

        try:
            client = self._get_client()
            response = await client.generate_content_async(prompt)
            raw_text = response.text.strip()

            # 提取 JSON 部分（LLM 输出可能包含多余文字）
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError(f"LLM 返回格式异常: {raw_text[:200]}")

            result_dict = json.loads(raw_text[start:end])
            return TrackResult(
                label=result_dict.get("label", "other"),
                confidence=float(result_dict.get("confidence", 0.0)),
                stage="llm",
                reason=result_dict.get("reason", ""),
            )

        except Exception as e:
            logger.error("llm_classify_failed", video_id=video.video_id, error=str(e))
            return TrackResult(label="other", confidence=0.0, stage="llm", reason=str(e))
