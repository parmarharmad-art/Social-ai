import hashlib
import hmac
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_billing_status_is_safe_and_does_not_expose_secrets(monkeypatch):
    import app.billing as billing
    monkeypatch.setattr(billing, "_config", lambda: {
        "key_id": "rzp_test_public",
        "key_secret": "private-secret",
        "plan_id": "plan_test_monthly",
        "webhook_secret": "hook-secret",
        "automation_key": "admin-key",
        "database_url": "postgresql://private",
    })
    response = client.get("/api/billing/status")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "razorpay"
    assert data["billing_model"] == "monthly_subscription"
    assert data["monthly_plan_configured"] is True
    assert data["customer_self_service_enabled"] is False
    assert "private-secret" not in response.text
    assert "postgresql://" not in response.text


def test_subscription_creation_requires_admin_key(monkeypatch):
    import app.billing as billing
    monkeypatch.setattr(billing, "_config", lambda: {
        "key_id": "rzp_test_public",
        "key_secret": "private-secret",
        "plan_id": "plan_test_monthly",
        "webhook_secret": "hook-secret",
        "automation_key": "admin-key",
        "database_url": "postgresql://private",
    })
    response = client.post("/api/billing/create-subscription", json={})
    assert response.status_code == 401


def test_subscription_creation_fails_closed_when_not_configured(monkeypatch):
    import app.billing as billing
    monkeypatch.setattr(billing, "_config", lambda: {
        "key_id": "",
        "key_secret": "",
        "plan_id": "",
        "webhook_secret": "",
        "automation_key": "admin-key",
        "database_url": "",
    })
    response = client.post(
        "/api/billing/create-subscription",
        headers={"X-Automation-Key": "admin-key"},
        json={},
    )
    assert response.status_code == 503


def test_billing_setup_page_loads():
    response = client.get("/billing")
    assert response.status_code == 200
    assert "RAZORPAY_PLAN_ID" in response.text
    assert "/webhooks/razorpay" in response.text


def test_razorpay_webhook_rejects_bad_signature(monkeypatch):
    import app.billing as billing
    monkeypatch.setattr(billing, "_config", lambda: {
        "key_id": "rzp_test_public",
        "key_secret": "private-secret",
        "plan_id": "plan_test_monthly",
        "webhook_secret": "correct-hook-secret",
        "automation_key": "admin-key",
        "database_url": "postgresql://private",
    })
    response = client.post(
        "/webhooks/razorpay",
        content=json.dumps({"event": "subscription.activated"}),
        headers={"X-Razorpay-Signature": "bad-signature", "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid webhook signature."
