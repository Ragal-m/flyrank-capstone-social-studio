import base64
import os

import pytest

from app.db import migrate
from app.settings import get_settings


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv(
        "ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode()
    )
    monkeypatch.setenv("WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setenv("ENABLE_WORKER", "false")
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("DEFAULT_TENANT_ID", "test-tenant")
    get_settings.cache_clear()
    migrate()
    yield
    get_settings.cache_clear()
