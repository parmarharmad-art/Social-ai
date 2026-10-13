import sys
from pathlib import Path

# Ensure the repository root is importable in CI and local test runs.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_homepage_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "SocialPilot AI" in response.text


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_instagram_start_requires_configuration(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "INSTAGRAM_APP_ID", "")
    monkeypatch.setattr(main, "REDIRECT_URI", "")
    response = client.get("/auth/instagram/start")
    assert response.status_code == 503


def test_content_ideas_endpoint():
    response = client.get("/api/content/ideas")
    assert response.status_code == 200
    data = response.json()
    assert data["brand"] == "Kiran Kumar • AI Automation"
    assert data["posts_per_day"] == 2
    assert len(data["topics"]) >= 10
    assert any("YouTube" in topic for topic in data["topics"])
    assert any("LinkedIn" in topic for topic in data["topics"])
    assert any("Meta Ads" in topic for topic in data["topics"])


def test_planner_page_loads():
    response = client.get("/planner")
    assert response.status_code == 200
    assert "SocialPilot AI" in response.text
    assert "Schedule post" in response.text
    assert "Automation API key" in response.text


def test_post_queue_requires_configured_automation_key(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "")
    response = client.get("/api/posts")
    assert response.status_code == 503


def test_post_queue_rejects_wrong_automation_key(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "test-key")
    response = client.get("/api/posts", headers={"X-Automation-Key": "wrong-key"})
    assert response.status_code == 401


def test_schedule_rejects_non_https_image_before_database_access(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "test-key")
    response = client.post(
        "/api/posts/schedule",
        headers={"X-Automation-Key": "test-key"},
        json={
            "topic": "Test topic",
            "image_url": "http://example.com/image.jpg",
            "instagram_user_id": "123",
            "scheduled_at": "2026-10-13T15:30:00+05:30",
        },
    )
    assert response.status_code == 400
    assert "HTTPS" in response.json()["detail"]


def test_schedule_rejects_timezone_missing_before_database_access(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "test-key")
    response = client.post(
        "/api/posts/schedule",
        headers={"X-Automation-Key": "test-key"},
        json={
            "topic": "Test topic",
            "image_url": "https://example.com/image.jpg",
            "instagram_user_id": "123",
            "scheduled_at": "2026-10-13T15:30:00",
        },
    )
    assert response.status_code == 400
    assert "ISO-8601 with timezone" in response.json()["detail"]


def test_automation_status_does_not_expose_secrets():
    response = client.get("/api/automation/status")
    assert response.status_code == 200
    data = response.json()
    assert "ai_text_configured" in data
    assert "comment_auto_reply_enabled" in data
    assert "sk-" not in str(data)
    assert "access_token" not in data


def test_ai_content_requires_automation_key(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "test-key")
    response = client.post("/api/ai/generate", json={"topic": "Instagram automation"})
    assert response.status_code == 401


def test_ai_content_requires_topic(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "test-key")
    response = client.post(
        "/api/ai/generate",
        headers={"X-Automation-Key": "test-key"},
        json={"topic": "   "},
    )
    assert response.status_code == 400


def test_ai_image_requires_prompt(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "test-key")
    response = client.post(
        "/api/ai/image",
        headers={"X-Automation-Key": "test-key"},
        json={},
    )
    assert response.status_code == 400


def test_webhook_verification_fails_closed_without_valid_token(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "META_WEBHOOK_VERIFY_TOKEN", "private-test-token")
    response = client.get(
        "/webhooks/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 403


def test_instagram_report_requires_automation_key(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "test-key")
    response = client.get("/api/reports/instagram?instagram_user_id=123")
    assert response.status_code == 401


def test_daily_queue_requires_automation_key(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "AUTOMATION_API_KEY", "test-key")
    response = client.post("/api/automation/queue-daily", json={"instagram_user_id": "123"})
    assert response.status_code == 401


def test_automation_status_reports_daily_content_flag():
    response = client.get("/api/automation/status")
    assert response.status_code == 200
    assert "automatic_daily_content_enabled" in response.json()
