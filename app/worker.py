import asyncio

import httpx

from .models import Platform
from .publishers import FakeInstagramPublisher, FakeXPublisher, PublishRequest
from .repository import (
    claim_due_post,
    encrypted_token,
    record_platform_acceptance,
    reschedule_post,
)
from .security import decrypt_token
from .settings import get_settings


def publisher_for(platform: Platform, client: httpx.AsyncClient):
    base_url = get_settings().fake_platform_base_url
    if platform == "instagram":
        return FakeInstagramPublisher(base_url, client)
    return FakeXPublisher(base_url, client)


async def process_due_once(client: httpx.AsyncClient | None = None) -> bool:
    post = claim_due_post()
    if post is None:
        return False
    owns_client = client is None
    client = client or httpx.AsyncClient()
    try:
        token = decrypt_token(encrypted_token(post["platform"]))
        request = PublishRequest(
            platform=post["platform"],
            caption=post["caption"],
            image_path=post["image_path"],
            idempotency_key=post["idempotency_key"],
            token=token,
        )
        result = await publisher_for(post["platform"], client).publish(request)
        record_platform_acceptance(post["id"], result.platform_post_id)
    except Exception as error:
        delay = min(2 ** min(post["attempts"], 6), 60)
        reschedule_post(post["id"], str(error), delay)
    finally:
        if owns_client:
            await client.aclose()
    return True


async def worker_loop(stop: asyncio.Event) -> None:
    async with httpx.AsyncClient() as client:
        while not stop.is_set():
            worked = await process_due_once(client)
            if not worked:
                try:
                    await asyncio.wait_for(
                        stop.wait(), timeout=get_settings().worker_poll_seconds
                    )
                except TimeoutError:
                    pass


