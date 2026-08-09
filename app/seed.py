from datetime import datetime, timedelta, timezone

import httpx

from .settings import get_settings


def main() -> None:
    payload = {
        "title": "Reliability is a product feature",
        "body": "Idempotency, durable scheduling, and verified webhooks make publishing safe.",
        "url": "https://example.com/reliability",
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat(),
    }
    response = httpx.post(
        f"{get_settings().app_base_url}/campaigns", json=payload, timeout=15
    )
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()


