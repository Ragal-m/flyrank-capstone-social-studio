import uuid
from datetime import datetime, timedelta, timezone

from .db import connect
from .models import CampaignCreate, Platform


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_token(platform: Platform, encrypted_value: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO tokens(platform, encrypted_value) VALUES(?, ?) "
            "ON CONFLICT(platform) DO UPDATE SET encrypted_value=excluded.encrypted_value",
            (platform, encrypted_value),
        )


def encrypted_token(platform: Platform) -> str:
    with connect() as connection:
        row = connection.execute(
            "SELECT encrypted_value FROM tokens WHERE platform=?", (platform,)
        ).fetchone()
    if row is None:
        raise LookupError(f"token not found for {platform}")
    return str(row["encrypted_value"])


def create_campaign_records(
    campaign_id: str,
    data: CampaignCreate,
    captions: dict[Platform, str],
    images: dict[Platform, str],
) -> None:
    created_at = iso_now()
    scheduled_at = data.scheduled_at.isoformat()
    with connect() as connection:
        connection.execute(
            "INSERT INTO campaigns(id,title,body,url,created_at) VALUES(?,?,?,?,?)",
            (campaign_id, data.title, data.body, str(data.url), created_at),
        )
        for platform in ("instagram", "x"):
            post_id = str(uuid.uuid4())
            key = f"{campaign_id}:{platform}"
            connection.execute(
                "INSERT INTO social_posts(id,campaign_id,platform,caption,image_path,status,"
                "scheduled_at,idempotency_key,next_attempt_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    post_id,
                    campaign_id,
                    platform,
                    captions[platform],
                    images[platform],
                    "queued",
                    scheduled_at,
                    key,
                    scheduled_at,
                ),
            )


def campaign(campaign_id: str) -> dict | None:
    with connect() as connection:
        root = connection.execute(
            "SELECT * FROM campaigns WHERE id=?", (campaign_id,)
        ).fetchone()
        if root is None:
            return None
        posts = connection.execute(
            "SELECT id,campaign_id,platform,caption,image_path,status,scheduled_at,"
            "platform_post_id,error FROM social_posts WHERE campaign_id=? ORDER BY platform",
            (campaign_id,),
        ).fetchall()
    return {**dict(root), "posts": [dict(post) for post in posts]}


def queue_campaign_now(campaign_id: str) -> int:
    now = iso_now()
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE social_posts SET status='queued',next_attempt_at=?,lease_until=NULL "
            "WHERE campaign_id=? AND status NOT IN ('published','failed')",
            (now, campaign_id),
        )
        return cursor.rowcount


def claim_due_post(lease_seconds: int = 30) -> dict | None:
    now = datetime.now(timezone.utc)
    lease_until = (now + timedelta(seconds=lease_seconds)).isoformat()
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM social_posts WHERE "
            "((status='queued' AND next_attempt_at<=?) OR "
            "(status='publishing' AND lease_until<?)) "
            "ORDER BY next_attempt_at LIMIT 1",
            (now.isoformat(), now.isoformat()),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            "UPDATE social_posts SET status='publishing',lease_until=?,attempts=attempts+1 "
            "WHERE id=?",
            (lease_until, row["id"]),
        )
        claimed = dict(row)
        claimed["attempts"] = int(row["attempts"]) + 1
        return claimed


def record_platform_acceptance(post_id: str, platform_post_id: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE social_posts SET platform_post_id=?,error=NULL WHERE id=?",
            (platform_post_id, post_id),
        )


def reschedule_post(post_id: str, error: str, delay_seconds: int) -> None:
    next_attempt = (datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)).isoformat()
    with connect() as connection:
        connection.execute(
            "UPDATE social_posts SET status='queued',next_attempt_at=?,lease_until=NULL,error=? "
            "WHERE id=?",
            (next_attempt, error[:500], post_id),
        )


def apply_delivery_event(
    event_id: str,
    idempotency_key: str,
    platform_post_id: str,
    status: str,
) -> bool:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        duplicate = connection.execute(
            "SELECT 1 FROM webhook_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if duplicate:
            return False
        cursor = connection.execute(
            "UPDATE social_posts SET status=?,platform_post_id=?,lease_until=NULL,error=NULL "
            "WHERE idempotency_key=?",
            (status, platform_post_id, idempotency_key),
        )
        if cursor.rowcount != 1:
            raise LookupError("post not found for delivery event")
        connection.execute(
            "INSERT INTO webhook_events(event_id,received_at) VALUES(?,?)",
            (event_id, iso_now()),
        )
        return True


def set_fake_rate_limit(platform: Platform, requests: int, retry_after: int) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO fake_rate_limits(platform,remaining,retry_after) VALUES(?,?,?) "
            "ON CONFLICT(platform) DO UPDATE SET remaining=excluded.remaining,"
            "retry_after=excluded.retry_after",
            (platform, requests, retry_after),
        )


def consume_fake_rate_limit(platform: Platform) -> int | None:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT remaining,retry_after FROM fake_rate_limits WHERE platform=?",
            (platform,),
        ).fetchone()
        if row is None or int(row["remaining"]) <= 0:
            return None
        connection.execute(
            "UPDATE fake_rate_limits SET remaining=remaining-1 WHERE platform=?",
            (platform,),
        )
        return int(row["retry_after"])


def fake_publish(
    platform: Platform, idempotency_key: str, caption: str
) -> tuple[str, bool]:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT platform_post_id FROM fake_posts WHERE idempotency_key=?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            return str(existing["platform_post_id"]), False
        platform_post_id = f"fake-{platform}-{uuid.uuid4().hex[:12]}"
        connection.execute(
            "INSERT INTO fake_posts(idempotency_key,platform_post_id,platform,caption,created_at) "
            "VALUES(?,?,?,?,?)",
            (idempotency_key, platform_post_id, platform, caption, iso_now()),
        )
        return platform_post_id, True


def fake_post_count() -> int:
    with connect() as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM fake_posts").fetchone()
    return int(row["count"])


