from datetime import datetime

from pydantic import BaseModel


class VideoResponse(BaseModel):
    id: int
    platform: str
    video_id: str
    track: str
    title: str
    author_id: str
    author_name: str
    cover_url: str | None = None
    track_confidence: float
    classify_stage: str
    discovery_source: str
    is_tracking: bool
    published_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrackResponse(BaseModel):
    name: str
    display_name: str
    description: str
    is_active: bool

    model_config = {"from_attributes": True}


class AddAccountRequest(BaseModel):
    platform: str = "douyin"
    account_id: str
    account_name: str = ""
    track: str
