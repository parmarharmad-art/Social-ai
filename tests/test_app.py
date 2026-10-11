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

    monkeypatch.setattr(main, "META_APP_ID", "")
    monkeypatch.setattr(main, "REDIRECT_URI", "")
    response = client.get("/auth/instagram/start")
    assert response.status_code == 503
