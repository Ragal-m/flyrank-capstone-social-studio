import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

import httpx

from .models import Platform


@dataclass(frozen=True)
class PublishRequest:
    platform: Platform
    caption: str
    image_path: str
    idempotency_key: str
    token: str


@dataclass(frozen=True)
class PublishResult:
    platform_post_id: str
    attempts: int


class SocialPublisher(Protocol):
    async def publish(self, request: PublishRequest) -> PublishResult: ...


class FakePlatformPublisher:
    def __init__(
        self,
        platform: Platform,
        base_url: str,
        client: httpx.AsyncClient,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.platform = platform
        self.base_url = base_url.rstrip("/")
        self.client = client
        self.sleeper = sleeper

    async def publish(self, request: PublishRequest) -> PublishResult:
        for attempt in range(1, 5):
            try:
                response = await self.client.post(
                    f"{self.base_url}/{self.platform}/posts",
                    json={"caption": request.caption, "image_path": request.image_path},
                    headers={
                        "Authorization": f"Bearer {request.token}",
                        "Idempotency-Key": request.idempotency_key,
                    },
                    timeout=10,
                )
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 4:
                    raise
                await self.sleeper(min(2 ** (attempt - 1), 8))
                continue
            if response.status_code == 429:
                if attempt == 4:
                    response.raise_for_status()
                wait = max(float(response.headers.get("Retry-After", "1")), 0)
                await self.sleeper(wait)
                continue
            if response.status_code >= 500 and attempt < 4:
                await self.sleeper(min(2 ** (attempt - 1), 8))
                continue
            response.raise_for_status()
            return PublishResult(
                platform_post_id=response.json()["platform_post_id"], attempts=attempt
            )
        raise RuntimeError("publish attempts exhausted")


class FakeInstagramPublisher(FakePlatformPublisher):
    def __init__(self, base_url: str, client: httpx.AsyncClient, sleeper=asyncio.sleep):
        super().__init__("instagram", base_url, client, sleeper)


class FakeXPublisher(FakePlatformPublisher):
    def __init__(self, base_url: str, client: httpx.AsyncClient, sleeper=asyncio.sleep):
        super().__init__("x", base_url, client, sleeper)


