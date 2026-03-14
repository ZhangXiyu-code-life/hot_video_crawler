"""
Stage1：关键词规则分类器。
基于 tracks.yaml 中的关键词列表进行正则/字符串匹配。
速度最快（O(1) 级别），覆盖约 60% 的视频。
"""
from app.classifier.schemas import TrackResult
from app.datasource.schemas import VideoMeta


class KeywordRuleClassifier:

    def __init__(self, tracks_config: dict) -> None:
        # 预处理：构建 track_name → (high_keywords, medium_keywords) 映射
        self._track_keywords: dict[str, tuple[list[str], list[str]]] = {}

        keywords_cfg = tracks_config  # 来自 keywords.yaml
        for track_name, kw_groups in keywords_cfg.items():
            high = [k.lower() for k in kw_groups.get("high_precision", [])]
            medium = [k.lower() for k in kw_groups.get("medium_precision", [])]
            self._track_keywords[track_name] = (high, medium)

    def classify(self, video: VideoMeta, track_name: str) -> TrackResult | None:
        """
        对视频进行关键词匹配。
        - 高精度关键词命中 → confidence 0.9
        - 中精度关键词命中 → confidence 0.75
        - 未命中 → 返回 None（交给下一阶段）
        """
        if track_name not in self._track_keywords:
            return None

        text = f"{video.title} {video.description} {video.author_bio}".lower()
        high_keywords, medium_keywords = self._track_keywords[track_name]

        for kw in high_keywords:
            if kw in text:
                return TrackResult(
                    label=track_name,
                    confidence=0.9,
                    stage="rule",
                    reason=f"高精度关键词命中：{kw}",
                )

        matched_medium = [kw for kw in medium_keywords if kw in text]
        if len(matched_medium) >= 2:
            return TrackResult(
                label=track_name,
                confidence=0.8,
                stage="rule",
                reason=f"中精度关键词多命中：{matched_medium[:3]}",
            )
        if len(matched_medium) == 1:
            return TrackResult(
                label=track_name,
                confidence=0.7,
                stage="rule",
                reason=f"中精度关键词单命中：{matched_medium[0]}",
            )

        return None
