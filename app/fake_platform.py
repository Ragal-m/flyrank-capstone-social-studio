import time
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Response
from pydantic import BaseModel, Field

from .models import Platform
from .repository import (
    consume_fake_rate_limit,
    fake_post_count,
    fake_publish,
    set_fake_rate_limit,
)
from .security import delivery_body, sign_payload
from .settings import get_settings


router = APIRouter(prefix="/fake", tags=["fake-platform"])


class FakePostInput(BaseModel):
    caption: str = Field(min_length=1, max_length=2_000)
    image_path: str = Field(min_length=1)


class RateLimitInput(BaseModel):
    requests: int = Field(default=1, ge=1, le=10)
    retry_after: int = Field(default=1, ge=0, le=60)


async def send_delivery(
    platform_post_id: str, idempotency_key: str, status: str = "published"
) -> None:
    event = {
        "event_id": str(uuid.uuid4()),
        "idempotency_key": idempotency_key,
        "platform_post_id": platform_post_id,
        "status": status,
        "timestamp": int(time.time()),
    }
    body = delivery_body(event)
    headers = {"Content-Type": "application/json", "X-Social-Signature": sign_payload(body)}
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{get_settings().app_base_url}/webhook/social-delivery",
            content=body,
            headers=headers,
            timeout=10,
        )


@router.post("/oauth/token")
def fake_oauth(platform: Platform) -> dict:
    return {"access_token": f"fake-token-{platform}", "token_type": "bearer"}


@router.post("/{platform}/posts")
def publish_post(
    platform: Platform,
    data: FakePostInput,
    background_tasks: BackgroundTasks,
    response: Response,
    authorization: str = Header(default=""),
    idempotency_key: str = Header(min_length=1),
) -> dict:
    if authorization != f"Bearer fake-token-{platform}":
        raise HTTPException(status_code=401, detail="invalid fake token")
    retry_after = consume_fake_rate_limit(platform)
    if retry_after is not None:
        response.headers["Retry-After"] = str(retry_after)
        response.status_code = 429
        return {"detail": "fake rate limit"}
    platform_post_id, created = fake_publish(platform, idempotency_key, data.caption)
    if created:
        background_tasks.add_task(send_delivery, platform_post_id, idempotency_key)
    return {"platform_post_id": platform_post_id, "created": created}


@router.post("/control/rate-limit/{platform}")
def configure_rate_limit(platform: Platform, data: RateLimitInput) -> dict:
    set_fake_rate_limit(platform, data.requests, data.retry_after)
    return {"platform": platform, **data.model_dump()}


@router.get("/posts/count")
def published_count() -> dict:
    return {"count": fake_post_count()}


