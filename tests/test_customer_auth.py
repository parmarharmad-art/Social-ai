import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
import app.customer_auth as auth

client = TestClient(app)


def test_account_page_loads():
    response = client.get("/account")
    assert response.status_code == 200
    assert "Create account" in response.text
    assert "Log in" in response.text


def test_password_hash_is_salted_and_verifiable():
    first = auth._hash_password("correct horse battery staple")
    second = auth._hash_password("correct horse battery staple")
    assert first != second
    assert auth._verify_password("correct horse battery staple", first)
    assert not auth._verify_password("wrong password", first)


def test_signed_session_round_trip_and_tamper_detection(monkeypatch):
    monkeypatch.setenv("CUSTOMER_SESSION_SECRET", "test-only-secret-that-is-long-enough-123456")
    token = auth._make_session("account-123")
    assert auth._read_session(token)["sub"] == "account-123"
    assert auth._read_session(token + "x") is None


def test_signup_disabled_by_default(monkeypatch):
    monkeypatch.setenv("CUSTOMER_SIGNUP_ENABLED", "false")
    response = client.post("/api/account/signup", json={
        "email": "buyer@example.com",
        "password": "a-long-test-password-123",
        "workspace_name": "Buyer workspace"
    })
    assert response.status_code == 503
    assert "not enabled" in response.json()["detail"]


def test_me_requires_login():
    response = client.get("/api/account/me")
    assert response.status_code == 401


def test_logout_clears_session_cookie():
    response = client.post("/api/account/logout")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "socialpilot_session" in response.headers.get("set-cookie", "")


def test_instagram_oauth_requires_customer_login(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "INSTAGRAM_APP_ID", "test-app-id")
    monkeypatch.setattr(main, "REDIRECT_URI", "https://example.com/auth/instagram/callback")
    response = client.get("/auth/instagram/start", follow_redirects=False)
    assert response.status_code == 401
    assert "Log in" in response.json()["detail"]


def test_facebook_oauth_requires_customer_login(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "FACEBOOK_APP_ID", "test-app-id")
    monkeypatch.setattr(main, "FACEBOOK_APP_SECRET", "test-secret")
    response = client.get("/auth/facebook/start", follow_redirects=False)
    assert response.status_code == 401
    assert "Log in" in response.json()["detail"]
