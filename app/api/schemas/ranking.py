from datetime import date, datetime

from pydantic import BaseModel


class RankingItemResponse(BaseModel):
    rank: int
    video_platform_id: str
    video_title: str
    author_name: str
    play_increment: int
    play_count_end: int
    cover_url: str | None = None

    model_config = {"from_attributes": True}


class RankingResponse(BaseModel):
    id: int
    period_type: str
    platform: str
    track: str
    period_start: date
    period_end: date
    top_n: int
    generated_at: datetime
    items: list[RankingItemResponse] = []

    model_config = {"from_attributes": True}


class RankingListResponse(BaseModel):
    total: int
    rankings: list[RankingResponse]
