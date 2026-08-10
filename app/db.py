import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .settings import get_settings


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS social_posts (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    tenant_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    caption TEXT NOT NULL,
    image_path TEXT NOT NULL,
    status TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    platform_post_id TEXT,
    error TEXT,
    lease_until TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT NOT NULL,
    UNIQUE(campaign_id, platform)
);
CREATE INDEX IF NOT EXISTS social_posts_due
ON social_posts(status, next_attempt_at, lease_until);
CREATE TABLE IF NOT EXISTS tokens (
    tenant_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    encrypted_value TEXT NOT NULL
    ,PRIMARY KEY(tenant_id, platform)
);
CREATE TABLE IF NOT EXISTS webhook_events (
    event_id TEXT PRIMARY KEY,
    received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fake_posts (
    idempotency_key TEXT PRIMARY KEY,
    platform_post_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    caption TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fake_rate_limits (
    platform TEXT PRIMARY KEY,
    remaining INTEGER NOT NULL,
    retry_after INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS failure_alerts (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    post_id TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS campaigns_tenant ON campaigns(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS posts_tenant_due ON social_posts(tenant_id, status, next_attempt_at);
"""


def database_path() -> Path:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path(), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def migrate() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(1,datetime('now'))"
        )
