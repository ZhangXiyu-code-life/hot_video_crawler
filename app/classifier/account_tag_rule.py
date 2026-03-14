"""
Stage2：账号标签规则分类器。
如果视频来自已知赛道的白名单账号，直接继承账号赛道标签，置信度 1.0。
"""
from app.classifier.schemas import TrackResult
from app.datasource.schemas import VideoMeta


class AccountTagClassifier:

    def __init__(self, account_track_map: dict[str, str]) -> None:
        """
        account_track_map: {account_id: track_name}
        由 VideoDiscoveryEngine 在初始化时从 DB 加载账号白名单构建。
        """
        self._map = account_track_map

    def classify(self, video: VideoMeta, track_name: str) -> TrackResult | None:
        """
        如果视频作者在白名单且赛道匹配，直接返回最高置信度结果。
        """
        known_track = self._map.get(video.author_id)
        if known_track and known_track == track_name:
            return TrackResult(
                label=track_name,
                confidence=1.0,
                stage="tag",
                reason=f"账号白名单直接命中：{video.author_id}",
            )
        return None
