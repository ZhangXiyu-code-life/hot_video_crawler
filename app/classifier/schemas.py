from dataclasses import dataclass


@dataclass
class TrackResult:
    """赛道分类结果。"""
    label: str               # 赛道名称，如 "knowledge_course" 或 "other"
    confidence: float        # 置信度 0.0 ~ 1.0
    stage: str               # 命中阶段："rule" | "tag" | "llm"
    reason: str = ""         # LLM 阶段的分类理由

    @property
    def is_match(self) -> bool:
        return self.label != "other" and self.confidence >= 0.6
