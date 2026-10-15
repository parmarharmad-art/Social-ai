"""Razorpay subscription integration for SocialPilot AI.

The initial subscription-creation endpoint is admin-protected by AUTOMATION_API_KEY.
Do not expose customer self-service checkout until authenticated customer accounts and
tenant isolation are implemented.
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
from uuid import uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _config():
    return {
        "key_id": os.getenv("RAZORPAY_KEY_ID", "").strip(),
        "key_secret": os.getenv("RAZORPAY_KEY_SECRET", "").strip(),
        "plan_id": os.getenv("RAZORPAY_PLAN_ID", "").strip(),
        "webhook_secret": os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip(),
        "automation_key": os.getenv("AUTOMATION_API_KEY", "").strip(),
        "database_url": os.getenv("DATABASE_URL", "").strip(),
    }


def _db():
    import psycopg
    url = _config()["database_url"]
    if not url:
        raise RuntimeError("DATABASE_URL is not configured.")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return psycopg.connect(url, connect_timeout=10)


def _require_admin(supplied: str | None):
    expected = _config()["automation_key"]
    if not expected or not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized.")


def _ensure_tables():
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS razorpay_subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'created',
                    short_url TEXT,
                    customer_id TEXT,
                    notes JSONB NOT NULL DEFAULT '{}'::jsonb,
                    last_event TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS razorpay_webhook_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        conn.commit()


@router.get("/api/billing/status")
async def razorpay_billing_status():
    c = _config()
    return {
        "provider": "razorpay",
        "billing_model": "monthly_subscription",
        "key_id_configured": bool(c["key_id"]),
        "key_secret_configured": bool(c["key_secret"]),
        "monthly_plan_configured": bool(c["plan_id"]),
        "webhook_secret_configured": bool(c["webhook_secret"]),
        "database_configured": bool(c["database_url"]),
        "checkout_creation_enabled": bool(c["key_id"] and c["key_secret"] and c["plan_id"] and c["database_url"]),
        "customer_self_service_enabled": False,
        "note": "Admin-created subscription links only until customer login and tenant isolation are implemented. No secret values are returned."
    }


@router.post("/api/billing/create-subscription")
async def create_monthly_subscription(payload: dict, x_automation_key: str | None = Header(default=None)):
    _require_admin(x_automation_key)
    c = _config()
    if not (c["key_id"] and c["key_secret"] and c["plan_id"] and c["database_url"]):
        raise HTTPException(status_code=503, detail="Configure RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_PLAN_ID and DATABASE_URL in Render.")
    # Razorpay's hosted subscription checkout collects the customer's payment details.
    # A random reference and notes make the subscription traceable without storing card data.
    reference_id = "spa_" + uuid4().hex[:24]
    notes = {"product": "SocialPilot AI", "billing": "monthly", "reference_id": reference_id}
    body = {
        "plan_id": c["plan_id"],
        "total_count": 120,
        "quantity": 1,
        "customer_notify": 1,
        "notes": notes
    }
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(
                "https://api.razorpay.com/v1/subscriptions",
                auth=(c["key_id"], c["key_secret"]),
                json=body
            )
    except httpx.HTTPError:
        logger.exception("Razorpay subscription request failed")
        raise HTTPException(status_code=502, detail="Could not reach Razorpay. Try again later.")
    if response.status_code >= 400:
        logger.warning("Razorpay subscription API rejected request: HTTP %s", response.status_code)
        raise HTTPException(status_code=502, detail="Razorpay rejected the subscription request. Verify the plan ID, API keys and account activation.")
    data = response.json()
    subscription_id = str(data.get("id") or "")
    short_url = data.get("short_url")
    if not subscription_id or not short_url:
        raise HTTPException(status_code=502, detail="Razorpay response did not include a subscription ID and checkout URL.")
    try:
        _ensure_tables()
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO razorpay_subscriptions
                    (subscription_id, plan_id, status, short_url, customer_id, notes)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (subscription_id) DO UPDATE SET
                      status=EXCLUDED.status, short_url=EXCLUDED.short_url,
                      customer_id=EXCLUDED.customer_id, notes=EXCLUDED.notes, updated_at=NOW()
                """, (subscription_id, c["plan_id"], str(data.get("status") or "created"),
                      short_url, data.get("customer_id"), json.dumps(notes)))
            conn.commit()
    except Exception:
        logger.exception("Could not save Razorpay subscription")
        raise HTTPException(status_code=503, detail="Subscription created at Razorpay but could not be saved locally. Check database and reconcile before retrying.")
    return {
        "ok": True,
        "provider": "razorpay",
        "billing": "monthly",
        "subscription_id": subscription_id,
        "checkout_url": short_url,
        "status": data.get("status", "created"),
        "note": "Share the hosted checkout link with the intended customer. Access should only be granted after a verified subscription-activated webhook and after customer account isolation is implemented."
    }


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    c = _config()
    if not c["webhook_secret"] or not c["database_url"]:
        raise HTTPException(status_code=503, detail="Razorpay webhook secret or database is not configured.")
    raw = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(c["webhook_secret"].encode(), raw, hashlib.sha256).hexdigest()
    if not signature or not secrets.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")
    try:
        body = json.loads(raw.decode("utf-8"))
        event_type = str(body.get("event") or "unknown")
        event_id = request.headers.get("x-razorpay-event-id") or hashlib.sha256(raw).hexdigest()
        entity = body.get("payload", {}).get("subscription", {}).get("entity", {}) or {}
        subscription_id = str(entity.get("id") or "")
        status = str(entity.get("status") or "")
    except (ValueError, UnicodeDecodeError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid webhook payload.")
    try:
        _ensure_tables()
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO razorpay_webhook_events (event_id,event_type) VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING event_id", (event_id, event_type))
                is_new = cur.fetchone()
                if is_new and subscription_id:
                    cur.execute("""
                        UPDATE razorpay_subscriptions
                        SET status=%s, last_event=%s, updated_at=NOW()
                        WHERE subscription_id=%s
                    """, (status or event_type, event_type, subscription_id))
            conn.commit()
    except Exception:
        logger.exception("Could not persist Razorpay webhook")
        raise HTTPException(status_code=503, detail="Could not persist webhook; Razorpay may retry.")
    return {"received": True, "event": event_type, "duplicate": not bool(is_new)}


@router.get("/billing", response_class=HTMLResponse, include_in_schema=False)
async def billing_setup_page():
    return HTMLResponse("""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>SocialPilot AI Billing Setup</title><style>body{font:16px/1.6 system-ui;max-width:760px;margin:24px auto;padding:0 16px;color:#172033}li{margin:10px 0}code{overflow-wrap:anywhere}main{border:1px solid #ddd;border-radius:14px;padding:20px}</style></head><body><main><h1>Razorpay monthly billing setup</h1><p>This page explains the owner setup; it does not ask customers for payment details.</p><ol><li>Create and activate your Razorpay merchant account and complete KYC.</li><li>Create a monthly recurring plan in Razorpay Dashboard and copy its plan ID.</li><li>In Render → socialpilot-ai-mvp → Environment, add <code>RAZORPAY_KEY_ID</code>, <code>RAZORPAY_KEY_SECRET</code>, <code>RAZORPAY_PLAN_ID</code>, and <code>RAZORPAY_WEBHOOK_SECRET</code>. Keep secrets private.</li><li>Configure the Razorpay webhook URL as <code>https://socialpilot-ai-mvp.onrender.com/webhooks/razorpay</code>. Subscribe to subscription activated, charged, pending, halted, cancelled, completed and paused events supported by your account.</li><li>Check <code>/api/billing/status</code> and run an owner-authorized test subscription. Test with Razorpay test-mode keys first.</li></ol><p><strong>Important:</strong> customer sign-in, tenant isolation and automatic access control are not implemented yet. Do not sell public self-service access or promise access will be automatically granted until those safeguards are built and tested.</p><p><a href="/sell">Product page</a> · <a href="/setup">General setup</a></p></main></body></html>""")
