from fastapi.testclient import TestClient

from app.main import app
from app.models import CampaignCreate
from app.repository import fail_post, failure_alerts
from app.service import create_campaign


def test_campaign_endpoints_require_authorization():
    with TestClient(app) as client:
        response = client.post(
            "/campaigns",
            json={"title": "No key", "body": "Rejected", "url": "https://example.com"},
        )
    assert response.status_code == 401


def test_terminal_worker_failure_creates_alert():
    campaign = create_campaign(
        CampaignCreate(title="Alert", body="Durable alert", url="https://example.com")
    )
    post = campaign.posts[0]
    fail_post(post.id, "test-tenant", "platform unavailable")
    alerts = failure_alerts()
    assert len(alerts) == 1
    assert alerts[0]["post_id"] == post.id
    assert alerts[0]["message"] == "platform unavailable"
