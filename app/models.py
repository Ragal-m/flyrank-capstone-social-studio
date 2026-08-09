from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


Platform = Literal["instagram", "x"]
PostStatus = Literal["queued", "publishing", "published", "failed"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20_000)
    url: HttpUrl
    scheduled_at: datetime = Field(default_factory=utc_now)

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("scheduled_at must include a timezone")
        return value.astimezone(timezone.utc)


class SocialPostEntry(BaseModel):
    id: str
    campaign_id: str
    platform: Platform
    caption: str
    image_path: str
    status: PostStatus
    scheduled_at: datetime
    platform_post_id: str | None
    error: str | None


class CampaignView(BaseModel):
    id: str
    title: str
    body: str
    url: str
    created_at: datetime
    posts: list[SocialPostEntry]


class DeliveryEvent(BaseModel):
    event_id: str
    idempotency_key: str
    platform_post_id: str
    status: Literal["published", "failed"]
    timestamp: int


