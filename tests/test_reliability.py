import asyncio

import httpx
import pytest

from app.models import CampaignCreate
from app.publishers import FakeXPublisher, PublishRequest
from app.repository import claim_due_post, fake_post_count, fake_publish
from app.service import create_campaign


def test_duplicate_publish_creates_one_platform_post():
    first_id, first_created = fake_publish("x", "campaign:x", "caption")
    second_id, second_created = fake_publish("x", "campaign:x", "caption")
    assert first_created is True
    assert second_created is False
    assert first_id == second_id
    assert fake_post_count() == 1


@pytest.mark.asyncio
async def test_rate_limit_honors_retry_after():
    calls = 0
    waits = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, json={"platform_post_id": "fake-x-1"})

    async def sleeper(seconds: float):
        waits.append(seconds)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        publisher = FakeXPublisher("https://fake.test", client, sleeper)
        result = await publisher.publish(
            PublishRequest("x", "caption", "image.png", "campaign:x", "token")
        )
    assert result.platform_post_id == "fake-x-1"
    assert result.attempts == 2
    assert waits == [3]
    assert calls == 2


@pytest.mark.asyncio
async def test_timeout_retry_reuses_idempotency_key():
    keys = []

    def handler(request: httpx.Request) -> httpx.Response:
        keys.append(request.headers["Idempotency-Key"])
        if len(keys) == 1:
            raise httpx.ReadTimeout("simulated timeout")
        return httpx.Response(200, json={"platform_post_id": "fake-x-2"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        publisher = FakeXPublisher("https://fake.test", client, asyncio.sleep)
        result = await publisher.publish(
            PublishRequest("x", "caption", "image.png", "stable-key", "token")
        )
    assert result.platform_post_id == "fake-x-2"
    assert keys == ["stable-key", "stable-key"]


def test_expired_worker_lease_is_reclaimed_without_changing_key():
    campaign = create_campaign(
        CampaignCreate(
            title="Crash recovery",
            body="A worker can resume this job safely.",
            url="https://example.com/recovery",
        )
    )
    first = claim_due_post(lease_seconds=-1)
    claim_due_post(lease_seconds=30)
    reclaimed = claim_due_post(lease_seconds=30)
    assert first["id"] == reclaimed["id"]
    assert first["idempotency_key"] == reclaimed["idempotency_key"]
    assert reclaimed["campaign_id"] == campaign.id

