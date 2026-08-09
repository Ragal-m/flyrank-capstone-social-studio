import json
import time
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.repository import encrypted_token, save_token
from app.security import decrypt_token, delivery_body, encrypt_token, sign_payload
from app.settings import get_settings


def campaign_payload():
    return {
        "title": "A reliable publisher",
        "body": "A durable campaign with trusted delivery state.",
        "url": "https://example.com/post",
        "scheduled_at": "2030-01-01T09:00:00Z",
    }


def test_tokens_use_random_nonce_and_round_trip():
    first = encrypt_token("secret-token")
    second = encrypt_token("secret-token")
    assert first != second
    assert decrypt_token(first) == "secret-token"
    save_token("instagram", first)
    assert encrypted_token("instagram") == first
    assert "secret-token" not in first
    database_bytes = open(get_settings().database_path, "rb").read()
    assert b"secret-token" not in database_bytes


def test_forged_webhook_is_rejected_and_valid_webhook_updates_status():
    with TestClient(app) as client:
        campaign = client.post("/campaigns", json=campaign_payload()).json()
        event = {
            "event_id": str(uuid.uuid4()),
            "idempotency_key": f"{campaign['id']}:instagram",
            "platform_post_id": "fake-instagram-proof",
            "status": "published",
            "timestamp": int(time.time()),
        }
        body = delivery_body(event)
        forged = client.post(
            "/webhook/social-delivery",
            content=body,
            headers={"X-Social-Signature": "forged"},
        )
        assert forged.status_code == 400
        unchanged = client.get(f"/campaigns/{campaign['id']}").json()
        instagram = next(p for p in unchanged["posts"] if p["platform"] == "instagram")
        assert instagram["status"] == "queued"
        valid = client.post(
            "/webhook/social-delivery",
            content=body,
            headers={"X-Social-Signature": sign_payload(body)},
        )
        assert valid.status_code == 200
        updated = client.get(f"/campaigns/{campaign['id']}").json()
        instagram = next(p for p in updated["posts"] if p["platform"] == "instagram")
        assert instagram["status"] == "published"


def test_modified_signed_body_is_rejected():
    event = {
        "event_id": str(uuid.uuid4()),
        "idempotency_key": "missing:x",
        "platform_post_id": "fake-x",
        "status": "published",
        "timestamp": int(time.time()),
    }
    body = delivery_body(event)
    signature = sign_payload(body)
    modified = json.dumps({**event, "status": "failed"}).encode()
    with TestClient(app) as client:
        response = client.post(
            "/webhook/social-delivery",
            content=modified,
            headers={"X-Social-Signature": signature},
        )
    assert response.status_code == 400

