import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

import httpx
import psycopg
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response

load_dotenv()

app = FastAPI(title="SocialPilot AI MVP", version="0.2.1")
logger = logging.getLogger(__name__)

INSTAGRAM_APP_ID = (os.getenv("INSTAGRAM_APP_ID") or os.getenv("META_APP_ID") or "1559704026184551").strip()
INSTAGRAM_APP_SECRET = (os.getenv("INSTAGRAM_APP_SECRET") or os.getenv("META_APP_SECRET") or "").strip()
REDIRECT_URI = os.getenv(
    "INSTAGRAM_REDIRECT_URI",
    "https://socialpilot-ai-mvp.onrender.com/auth/instagram/callback",
).strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
AUTOMATION_API_KEY = os.getenv("AUTOMATION_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://socialpilot-ai-mvp.onrender.com").strip().rstrip("/")
META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "").strip()
AUTO_REPLY_ENABLED = os.getenv("AUTO_REPLY_ENABLED", "false").strip().lower() == "true"
AUTO_CONTENT_ENABLED = os.getenv("AUTO_CONTENT_ENABLED", "false").strip().lower() == "true"
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "").strip()

oauth_states: dict[str, dict] = {}
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v25.0").strip() or "v25.0"


def database_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return psycopg.connect(url, connect_timeout=10)


def token_cipher():
    if not TOKEN_ENCRYPTION_KEY:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not configured.")
    return Fernet(TOKEN_ENCRYPTION_KEY.encode("ascii"))


def save_encrypted_token(user_id: str, access_token: str, expires_in: int | None, auth_method: str = "instagram_login"):
    encrypted = token_cipher().encrypt(access_token.encode("utf-8")).decode("ascii")
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS instagram_connections (
                    instagram_user_id TEXT PRIMARY KEY,
                    encrypted_access_token TEXT NOT NULL,
                    token_expires_in BIGINT,
                    auth_method TEXT NOT NULL DEFAULT 'instagram_login',
                    connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE instagram_connections ADD COLUMN IF NOT EXISTS auth_method TEXT NOT NULL DEFAULT 'instagram_login'")
            cur.execute("""
                INSERT INTO instagram_connections
                    (instagram_user_id, encrypted_access_token, token_expires_in, auth_method)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (instagram_user_id) DO UPDATE SET
                    encrypted_access_token = EXCLUDED.encrypted_access_token,
                    token_expires_in = EXCLUDED.token_expires_in,
                    auth_method = EXCLUDED.auth_method,
                    updated_at = NOW()
            """, (user_id, encrypted, expires_in, auth_method))
        conn.commit()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SocialPilot AI</title><style>body{font:16px system-ui;max-width:760px;margin:40px auto;padding:0 18px;color:#18212f}
    .card{border:1px solid #d9e0e8;border-radius:16px;padding:22px}a{display:inline-block;background:#1769e0;color:white;padding:12px 16px;border-radius:9px;text-decoration:none}</style></head>
    <body><div class="card"><h1>SocialPilot AI</h1><p>Instagram Creator account connection.</p>
    <p><a href="/setup">Setup checklist</a> <a href="/auth/instagram/start">Instagram Login</a> <a href="/auth/facebook/start">Facebook Login</a> <a href="/studio">Open Post & Video Studio</a> <a href="/planner">Content Planner</a></p>
    <p>Encrypted token storage requires DATABASE_URL and TOKEN_ENCRYPTION_KEY configuration.</p></div></body></html>
    """


@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    """Non-technical setup checklist; shows configuration status without exposing secrets."""
    checks = [
        ("OpenAI API key", bool(OPENAI_API_KEY), "Required for AI captions and image generation. Add OPENAI_API_KEY in Render Environment."),
        ("Persistent database", bool(DATABASE_URL), "Required to save the Instagram connection, post queue and generated images. Create/attach PostgreSQL in Render and set DATABASE_URL."),
        ("Token encryption key", bool(TOKEN_ENCRYPTION_KEY), "Required to store the Instagram token safely. Generate a Fernet key once and save it as TOKEN_ENCRYPTION_KEY. Do not rotate it after connecting without a migration."),
        ("Automation API key", bool(AUTOMATION_API_KEY), "Required by planner APIs and MCP tools. Set a long random secret as AUTOMATION_API_KEY."),
        ("Meta app secret", bool(INSTAGRAM_APP_SECRET), "Required for Instagram OAuth. Set META_APP_ID and META_APP_SECRET from your Meta developer app."),
        ("MCP access token", bool(os.getenv("MCP_ACCESS_TOKEN", "").strip() or AUTOMATION_API_KEY), "Required to protect remote MCP access. Set MCP_ACCESS_TOKEN (or use AUTOMATION_API_KEY as the fallback)."),
        ("Webhook verify token", bool(META_WEBHOOK_VERIFY_TOKEN), "Required only for comment webhooks. Set the same private value in Render and Meta."),
    ]
    rows = "".join(
        "<li><strong>" + ("READY" if ok else "NEEDS SETUP") + " — " + name + ".</strong> " + help_text + "</li>"
        for name, ok, help_text in checks
    )
    ready_count = sum(1 for _, ok, _ in checks if ok)
    return """<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SocialPilot AI Setup</title><style>body{font:16px/1.55 system-ui;max-width:820px;margin:24px auto;padding:0 16px;color:#172033;background:#f7f9fc}
    main{background:white;border:1px solid #dce3ed;border-radius:16px;padding:22px}a{color:#075dd8}li{margin:14px 0}code{overflow-wrap:anywhere}
    .note{background:#f1f5fb;padding:12px;border-radius:10px}.links a{display:inline-block;margin:5px 8px 5px 0}</style></head><body><main>
    <h1>SocialPilot AI — Setup checklist</h1>
    <p>Use this page to see which server settings are present. It never displays the secret values.</p>
    <p><strong>Configuration checks passing: """ + str(ready_count) + """ / """ + str(len(checks)) + """</strong></p><ul>""" + rows + """</ul>
    <h2>Finish setup in this order</h2><ol>
    <li>In Render, open the <strong>socialpilot-ai-mvp</strong> service → Environment. Add the missing variables listed above, then save and redeploy.</li>
    <li>Attach a persistent PostgreSQL database and set DATABASE_URL. Generate a Fernet key for TOKEN_ENCRYPTION_KEY and keep it safe.</li>
    <li>For Instagram Login, configure redirect URL <code>https://socialpilot-ai-mvp.onrender.com/auth/instagram/callback</code>. For the alternate Facebook Login flow, enable Facebook Login and add <code>https://socialpilot-ai-mvp.onrender.com/auth/facebook/callback</code> under Valid OAuth Redirect URIs. Request the Page and Instagram permissions used by that flow.</li>
    <li>Open Connect Instagram below and approve the requested access. After callback, confirm token_saved is true.</li>
    <li>Test a draft and image in Planner/Studio first. Schedule one test post before enabling daily automation.</li>
    <li>Keep automatic replies and automatic daily content disabled until a controlled test succeeds. Comment webhooks require Meta webhook setup and the relevant permissions.</li>
    </ol><p class="note"><strong>Important:</strong> never send API keys, app secrets, access tokens, or database URLs in chat or commit them to GitHub. A green configuration check only means a value exists; it does not prove Meta permissions or publishing work.</p>
    <p class="links"><a href="/">Dashboard</a><a href="/auth/instagram/start">Instagram Login</a><a href="/auth/facebook/start">Facebook Login</a><a href="/planner">Content Planner</a><a href="/studio">Post & Video Studio</a><a href="/api/automation/status">Configuration status</a></p>
    </main></body></html>"""


@app.get("/health")
async def health():
    return {"status": "ok", "service": "socialpilot-ai-mvp"}


@app.get("/diagnostics/oauth-config")
async def oauth_config_check():
    return {
        "instagram_app_id": INSTAGRAM_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "secret_configured": bool(INSTAGRAM_APP_SECRET),
        "database_configured": bool(DATABASE_URL),
        "encryption_key_configured": bool(TOKEN_ENCRYPTION_KEY),
    }


@app.get("/auth/instagram/start")
async def instagram_start():
    if not INSTAGRAM_APP_ID or not REDIRECT_URI:
        raise HTTPException(status_code=503, detail="Configure Instagram App ID and redirect URI.")
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {"redirect_uri": REDIRECT_URI, "auth_method": "instagram_login"}
    params = {
        "client_id": INSTAGRAM_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_comments,instagram_business_manage_insights",
        "state": state,
    }
    return RedirectResponse("https://www.instagram.com/oauth/authorize?" + urlencode(params), status_code=302)


@app.get("/auth/instagram/callback")
async def instagram_callback(request: Request, code: str | None = None,
                             state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"connected": False, "error": "Instagram authorization was cancelled or denied."})
    if not code or not state or state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    state_data = oauth_states.pop(state)
    exchange_redirect_uri = state_data["redirect_uri"]
    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET or not exchange_redirect_uri:
        raise HTTPException(status_code=503, detail="Instagram OAuth environment is not configured.")

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": INSTAGRAM_APP_ID,
                "client_secret": INSTAGRAM_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": exchange_redirect_uri,
                "code": code,
            },
        )
        if response.status_code >= 400:
            try:
                payload = response.json()
                err = payload.get("error", payload) if isinstance(payload, dict) else {}
                if not isinstance(err, dict):
                    err = {}
                err_type = err.get("type") or err.get("error_type")
                err_code = err.get("code")
                err_message = str(err.get("message") or err.get("error_message") or "No error message returned")[:300]
            except (ValueError, TypeError):
                err_type = err_code = None
                err_message = "No error message returned"
            logger.warning("Instagram token exchange failed: status=%s type=%s code=%s message=%s",
                           response.status_code, err_type or "unknown", err_code or "unknown", err_message)
            return JSONResponse(status_code=502, content={
                "connected": False, "error": "Instagram token exchange failed.",
                "meta_http_status": response.status_code, "meta_error_type": err_type,
                "meta_error_code": err_code, "meta_error_message": err_message,
            })
        token_data = response.json()
        short_token = token_data.get("access_token")
        if not short_token:
            raise HTTPException(status_code=502, detail="Instagram did not return an access token.")
        long_response = await client.get(
            "https://graph.instagram.com/access_token",
            params={"grant_type": "ig_exchange_token", "client_secret": INSTAGRAM_APP_SECRET,
                    "access_token": short_token},
        )
        if long_response.status_code >= 400:
            try:
                payload = long_response.json()
                err = payload.get("error", payload) if isinstance(payload, dict) else {}
                if not isinstance(err, dict):
                    err = {}
                err_type = err.get("type") or err.get("error_type")
                err_code = err.get("code")
                err_subcode = err.get("error_subcode")
                err_message = str(err.get("message") or err.get("error_message") or "No error message returned")[:300]
            except (ValueError, TypeError):
                err_type = err_code = err_subcode = None
                err_message = "No error message returned"
            logger.warning("Instagram long-lived token exchange failed: status=%s type=%s code=%s subcode=%s message=%s",
                           long_response.status_code, err_type or "unknown", err_code or "unknown",
                           err_subcode or "unknown", err_message)
            return JSONResponse(status_code=502, content={
                "connected": False,
                "error": "Instagram long-lived token exchange failed.",
                "meta_http_status": long_response.status_code,
                "meta_error_type": err_type,
                "meta_error_code": err_code,
                "meta_error_subcode": err_subcode,
                "meta_error_message": err_message,
            })
        long_data = long_response.json()
        long_token = long_data.get("access_token")
        expires_in = long_data.get("expires_in")

    if not long_token:
        raise HTTPException(status_code=502, detail="Instagram did not return a long-lived access token.")
    instagram_user_id = str(token_data.get("user_id") or "")
    if not instagram_user_id:
        raise HTTPException(status_code=502, detail="Instagram did not return a user ID.")

    try:
        save_encrypted_token(instagram_user_id, long_token, expires_in, "instagram_login")
    except Exception:
        logger.exception("Secure Instagram token storage failed; token value was not logged.")
        return JSONResponse(status_code=503, content={
            "connected": False,
            "error": "Instagram login succeeded, but secure token storage is not ready. Configure DATABASE_URL and TOKEN_ENCRYPTION_KEY, then reconnect.",
        })

    return {
        "connected": True,
        "token_saved": True,
        "storage": "encrypted_postgresql",
        "message": "Instagram connected and token stored encrypted. Publishing still requires a live test and Meta permission approval.",
        "user_id": instagram_user_id,
        "expires_in": expires_in,
    }


@app.get("/auth/facebook/start")
async def facebook_login_start():
    """Alternate official Instagram API with Facebook Login for Instagram professional accounts linked to a Page."""
    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
        raise HTTPException(status_code=503, detail="Configure Meta App ID and App Secret in Render.")
    redirect_uri = APP_BASE_URL + "/auth/facebook/callback"
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {"redirect_uri": redirect_uri, "auth_method": "facebook_login"}
    permissions = "pages_show_list,pages_read_engagement,instagram_basic,instagram_content_publish,instagram_manage_comments,instagram_manage_insights"
    params = {"client_id": INSTAGRAM_APP_ID, "redirect_uri": redirect_uri, "response_type": "code",
              "scope": permissions, "state": state}
    return RedirectResponse(f"https://www.facebook.com/{META_GRAPH_API_VERSION}/dialog/oauth?" + urlencode(params), status_code=302)


@app.get("/auth/facebook/callback")
async def facebook_login_callback(code: str | None = None, state: str | None = None,
                                  error: str | None = None, error_description: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"connected": False, "auth_method": "facebook_login",
            "error": "Facebook authorization was cancelled or denied.", "meta_error": str(error)[:100]})
    if not code or not state or state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    state_data = oauth_states.pop(state)
    if state_data.get("auth_method") != "facebook_login":
        raise HTTPException(status_code=400, detail="OAuth state does not match Facebook Login.")
    redirect_uri = state_data["redirect_uri"]
    base = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"
    async with httpx.AsyncClient(timeout=30) as client:
        token_response = await client.get(f"{base}/oauth/access_token", params={
            "client_id": INSTAGRAM_APP_ID, "client_secret": INSTAGRAM_APP_SECRET,
            "redirect_uri": redirect_uri, "code": code})
        if token_response.status_code >= 400:
            logger.warning("Facebook OAuth code exchange failed with HTTP %s", token_response.status_code)
            return JSONResponse(status_code=502, content={"connected": False, "auth_method": "facebook_login",
                "error": "Facebook OAuth code exchange failed.", "meta_http_status": token_response.status_code})
        short_token = token_response.json().get("access_token")
        if not short_token:
            raise HTTPException(status_code=502, detail="Facebook did not return a user access token.")
        long_response = await client.get(f"{base}/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": INSTAGRAM_APP_ID,
            "client_secret": INSTAGRAM_APP_SECRET, "fb_exchange_token": short_token})
        if long_response.status_code >= 400:
            logger.warning("Facebook long-lived token exchange failed with HTTP %s", long_response.status_code)
            return JSONResponse(status_code=502, content={"connected": False, "auth_method": "facebook_login",
                "error": "Facebook long-lived token exchange failed.", "meta_http_status": long_response.status_code})
        user_data = long_response.json()
        user_token = user_data.get("access_token")
        if not user_token:
            raise HTTPException(status_code=502, detail="Facebook did not return a long-lived user token.")
        pages_response = await client.get(f"{base}/me/accounts", params={
            "fields": "id,name,access_token,tasks,instagram_business_account", "access_token": user_token})
        if pages_response.status_code >= 400:
            logger.warning("Facebook Page lookup failed with HTTP %s", pages_response.status_code)
            return JSONResponse(status_code=502, content={"connected": False, "auth_method": "facebook_login",
                "error": "Could not list Facebook Pages. Check Page-list and engagement permissions.",
                "meta_http_status": pages_response.status_code})
        pages = pages_response.json().get("data", [])
        linked_page = next((p for p in pages if p.get("instagram_business_account", {}).get("id") and p.get("access_token")), None)
        if not linked_page:
            return JSONResponse(status_code=400, content={"connected": False, "auth_method": "facebook_login",
                "error": "No accessible Facebook Page linked to an Instagram professional account was found. Check Page access and linkage."})
        instagram_user_id = str(linked_page["instagram_business_account"]["id"])
        page_token = linked_page["access_token"]
        expires_in = user_data.get("expires_in")
    try:
        save_encrypted_token(instagram_user_id, page_token, expires_in, "facebook_login")
    except Exception:
        logger.exception("Secure Facebook Login token storage failed; token value was not logged.")
        return JSONResponse(status_code=503, content={"connected": False, "auth_method": "facebook_login",
            "error": "Facebook login succeeded, but secure token storage failed. Check database and encryption configuration."})
    return {"connected": True, "token_saved": True, "auth_method": "facebook_login",
            "instagram_user_id": instagram_user_id, "facebook_page_name": linked_page.get("name"),
            "message": "Facebook Login connected. Test publishing before enabling automation.", "expires_in": expires_in}


# Scheduled publishing MVP. Requires a persistent PostgreSQL database and a public HTTPS image URL.
def require_automation_key(provided: str | None):
    if not AUTOMATION_API_KEY:
        raise HTTPException(status_code=503, detail="AUTOMATION_API_KEY is not configured on the server.")
    if not provided or not secrets.compare_digest(provided, AUTOMATION_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid automation key.")


def ensure_posts_table():
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id BIGSERIAL PRIMARY KEY,
                    instagram_user_id TEXT NOT NULL,
                    image_url TEXT NOT NULL,
                    caption TEXT NOT NULL,
                    scheduled_at TIMESTAMPTZ NOT NULL,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    instagram_media_id TEXT,
                    last_error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    published_at TIMESTAMPTZ
                )
            """)
        conn.commit()


def make_caption(topic: str, call_to_action: str = "Follow @officialkiraankumar for practical AI automation workflows.") -> str:
    clean_topic = " ".join(topic.split()).strip()
    if not clean_topic:
        raise HTTPException(status_code=400, detail="topic is required.")
    return f"{clean_topic}\n\nSave this workflow for later and share it with someone who needs it.\n\n{call_to_action}\n\n#AIAutomation #DigitalMarketing #Automation #AITools #KiranKumar"


async def publish_due_posts():
    if not DATABASE_URL or not TOKEN_ENCRYPTION_KEY:
        return
    try:
        ensure_posts_table()
        # Claim due jobs in a short DB transaction to avoid duplicate processing.
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, instagram_user_id, image_url, caption
                    FROM scheduled_posts
                    WHERE status='scheduled' AND scheduled_at <= NOW()
                    ORDER BY scheduled_at
                    LIMIT 5
                    FOR UPDATE SKIP LOCKED
                """)
                jobs = cur.fetchall()
                for job in jobs:
                    cur.execute("UPDATE scheduled_posts SET status='processing' WHERE id=%s", (job[0],))
            conn.commit()
        for post_id, user_id, image_url, caption in jobs:
            try:
                with database_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT encrypted_access_token, auth_method FROM instagram_connections WHERE instagram_user_id=%s", (user_id,))
                        row = cur.fetchone()
                if not row:
                    raise RuntimeError("No saved Instagram connection for this account.")
                token = token_cipher().decrypt(row[0].encode("ascii")).decode("utf-8")
                auth_method = row[1] or "instagram_login"
                api_prefix = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}" if auth_method == "facebook_login" else "https://graph.instagram.com"
                async with httpx.AsyncClient(timeout=30) as client:
                    media = await client.post(
                        f"{api_prefix}/{user_id}/media",
                        data={"image_url": image_url, "caption": caption, "access_token": token},
                    )
                    media.raise_for_status()
                    media_id = media.json().get("id")
                    if not media_id:
                        raise RuntimeError("Instagram did not return a media container ID.")
                    published = await client.post(
                        f"{api_prefix}/{user_id}/media_publish",
                        data={"creation_id": media_id, "access_token": token},
                    )
                    published.raise_for_status()
                    published_id = published.json().get("id")
                with database_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE scheduled_posts SET status='published', instagram_media_id=%s, published_at=NOW(), last_error=NULL WHERE id=%s", (published_id, post_id))
                    conn.commit()
            except Exception as exc:
                logger.exception("Scheduled Instagram post %s failed", post_id)
                with database_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE scheduled_posts SET status='failed', last_error=%s WHERE id=%s", (str(exc)[:500], post_id))
                    conn.commit()
    except Exception:
        logger.exception("Scheduled publishing poll failed")


async def scheduler_loop():
    while True:
        await publish_due_posts()
        try:
            await maybe_queue_daily_content()
        except Exception:
            logger.exception("Automatic daily content queue check failed")
        await asyncio.sleep(30)


@app.on_event("startup")
async def start_scheduler():
    if DATABASE_URL and TOKEN_ENCRYPTION_KEY:
        asyncio.create_task(scheduler_loop())


@app.post("/api/posts/schedule")
async def schedule_post(payload: dict, x_automation_key: str | None = Header(default=None)):
    require_automation_key(x_automation_key)
    image_url = str(payload.get("image_url", "")).strip()
    topic = str(payload.get("topic", "")).strip()
    caption = str(payload.get("caption", "")).strip()
    user_id = str(payload.get("instagram_user_id", "")).strip()
    scheduled_at = str(payload.get("scheduled_at", "")).strip()
    if not image_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="image_url must be a public HTTPS image URL.")
    if not user_id or not scheduled_at:
        raise HTTPException(status_code=400, detail="instagram_user_id and scheduled_at are required.")
    if not caption:
        caption = make_caption(topic)
    try:
        when = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError("Timezone required")
        when = when.astimezone(timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="scheduled_at must be ISO-8601 with timezone, e.g. 2026-10-13T15:30:00+05:30.")
    try:
        ensure_posts_table()
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM instagram_connections WHERE instagram_user_id=%s", (user_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=400, detail="This Instagram account is not connected with a saved token. Reconnect Instagram first.")
                cur.execute("INSERT INTO scheduled_posts (instagram_user_id, image_url, caption, scheduled_at) VALUES (%s,%s,%s,%s) RETURNING id,status,scheduled_at", (user_id, image_url, caption, when))
                row = cur.fetchone()
            conn.commit()
        return {"ok": True, "post_id": row[0], "status": row[1], "scheduled_at": row[2].isoformat(), "caption": caption}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not schedule Instagram post")
        raise HTTPException(status_code=503, detail="Could not schedule post. Check DATABASE_URL and TOKEN_ENCRYPTION_KEY.")


@app.get("/api/posts")
async def list_posts(x_automation_key: str | None = Header(default=None)):
    require_automation_key(x_automation_key)
    try:
        ensure_posts_table()
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, instagram_user_id, caption, scheduled_at, status, instagram_media_id, last_error FROM scheduled_posts ORDER BY scheduled_at DESC LIMIT 50")
                rows = cur.fetchall()
        return {"posts": [{"id":r[0],"instagram_user_id":r[1],"caption":r[2],"scheduled_at":r[3].isoformat(),"status":r[4],"instagram_media_id":r[5],"last_error":r[6]} for r in rows]}
    except Exception:
        logger.exception("Could not list scheduled posts")
        raise HTTPException(status_code=503, detail="Could not load posts. Check database configuration.")


CONTENT_TOPICS = [
    "Automate YouTube Shorts from idea to publishing",
    "LinkedIn lead generation workflow with AI",
    "Meta Ads reporting automation with Google Sheets",
    "WhatsApp lead follow-up automation",
    "Automate social media content from research to publishing",
    "Claude AI workflow for marketing campaign briefs",
    "ChatGPT to Canva: turn a brief into carousel content",
    "Google Ads weekly reporting automation",
    "GA4 insights to an automated weekly report",
    "Connect apps using Make without coding",
    "Zapier workflow to capture and follow up leads",
    "n8n workflow for content approval",
    "MCP explained: connect AI to your work tools",
    "AI content calendar in Google Sheets",
    "Repurpose one long video into short-form content",
    "Lead form to CRM to WhatsApp follow-up workflow",
    "Human approval step in AI automation",
    "Automated client onboarding for freelancers",
    "Small business marketing dashboard automation",
    "Instagram content approval workflow"
]


@app.get("/api/content/ideas")
async def content_ideas():
    return {
        "brand": "Kiran Kumar • AI Automation",
        "language": "English",
        "posts_per_day": 2,
        "topics": CONTENT_TOPICS,
        "note": "Topic ideas only. AI-written content and image generation are not connected in this MVP."
    }


@app.get("/planner", response_class=HTMLResponse)
async def content_planner():
    topics_html = "".join(
        "<option>" + topic.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</option>"
        for topic in CONTENT_TOPICS
    )
    return """<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SocialPilot AI Planner</title><style>
    body{font:16px system-ui;max-width:720px;margin:20px auto;padding:0 14px;background:#0b1220;color:#edf3ff}
    section{background:#152238;padding:18px;border-radius:14px;margin:12px 0}label{display:block;margin:12px 0 5px;font-weight:600}
    input,select,textarea{width:100%;padding:12px;box-sizing:border-box;border-radius:8px;border:1px solid #52627a;background:#0b1220;color:white}
    button,a{display:inline-block;margin:8px 5px 0 0;padding:12px 14px;background:#2877ee;color:white;border:0;border-radius:8px;text-decoration:none;font:inherit}
    #result{white-space:pre-wrap;overflow-wrap:anywhere}</style></head><body>
    <h1>SocialPilot AI — Content Planner</h1><p><a href="/studio">Open built-in Post & Video Studio</a> · Choose a topic, prepare a caption, and schedule a post.</p>
    <section><p><a href="/auth/instagram/start">Instagram Login</a> <a href="/auth/facebook/start">Facebook Login (alternate)</a> <a href="/health">Check service</a></p>
    <label>Topic</label><select id="topic">""" + topics_html + """</select>
    <label>Public HTTPS image URL</label><input id="img" placeholder="Generated image URL appears here">
    <label>Instagram user ID</label><input id="uid" value="28750627681259473">
    <label>Schedule date and time (India)</label><input id="when" type="datetime-local">
    <label>Automation API key (entered only for this session)</label><input id="key" type="password" autocomplete="off">
    <label>AI image prompt</label><textarea id="imagePrompt" rows="3" placeholder="Describe the Instagram infographic you want"></textarea>
    <label>Generated content package (editable)</label><textarea id="aiContent" rows="8" placeholder="AI carousel slides and caption will appear here"></textarea>
    <label>Caption (editable)</label><textarea id="caption" rows="6"></textarea>
    <button onclick="preview()">Make template caption</button><button onclick="generateAIContent()">Generate AI content</button><button onclick="generateAIImage()">Generate AI image</button><button onclick="queueDaily()">Queue tomorrow's 2 posts</button><button onclick="schedule()">Schedule post</button>
    <div id="result">Add OpenAI API key in Render to enable AI content and image creation.</div></section>
    <section><h2>Instagram report</h2><button onclick="loadReport()">Load recent post report</button><div id="report">Report not loaded.</div></section>
    <section><h2>Post queue</h2><button onclick="refreshPosts()">Refresh posts</button><div id="queue">No queue loaded.</div></section>
    <script>
    function makeCaption(){return document.getElementById('topic').value+'\\n\\nSave this workflow for later and share it with someone who needs it.\\n\\nFollow @officialkiraankumar for practical AI automation workflows.\\n\\n#AIAutomation #DigitalMarketing #Automation #AITools #KiranKumar'}
    function preview(){document.getElementById('caption').value=makeCaption();document.getElementById('result').textContent='Caption template prepared.'}
    function apiKey(){const k=document.getElementById('key').value.trim();if(!k)throw Error('Enter the automation key from Render.');return k}
    async function generateAIContent(){const out=document.getElementById('result');try{const r=await fetch('/api/ai/generate',{method:'POST',headers:{'Content-Type':'application/json','X-Automation-Key':apiKey()},body:JSON.stringify({topic:document.getElementById('topic').value})});const d=await r.json();if(!r.ok)throw Error(d.detail||'AI generation failed');document.getElementById('aiContent').value=d.content;document.getElementById('caption').value=d.content;const m=d.content.match(/IMAGE PROMPT[:\\s]+([\\s\\S]*?)(?:\\n[A-Z][A-Z ]{2,}:|$)/i);if(m)document.getElementById('imagePrompt').value=m[1].trim();out.textContent='AI content created. Review/edit the caption before scheduling.'}catch(e){out.textContent='AI content not created: '+e.message}}
    async function generateAIImage(){const out=document.getElementById('result');try{const prompt=document.getElementById('imagePrompt').value.trim();if(!prompt)throw Error('Enter an image prompt or generate AI content first.');const r=await fetch('/api/ai/image',{method:'POST',headers:{'Content-Type':'application/json','X-Automation-Key':apiKey()},body:JSON.stringify({prompt})});const d=await r.json();if(!r.ok)throw Error(d.detail||'Image generation failed');document.getElementById('img').value=d.image_url;out.textContent='Image generated and stored. Image URL added to the post form.'}catch(e){out.textContent='AI image not created: '+e.message}}
    async function queueDaily(){const out=document.getElementById('result');try{const r=await fetch('/api/automation/queue-daily',{method:'POST',headers:{'Content-Type':'application/json','X-Automation-Key':apiKey()},body:JSON.stringify({instagram_user_id:document.getElementById('uid').value.trim()})});const d=await r.json();if(!r.ok)throw Error(d.detail||'Queue failed');out.textContent='Daily queue created: '+JSON.stringify(d.posts)}catch(e){out.textContent='Daily queue not created: '+e.message}}
    async function loadReport(){const box=document.getElementById('report');try{const r=await fetch('/api/reports/instagram?instagram_user_id='+encodeURIComponent(document.getElementById('uid').value.trim()),{headers:{'X-Automation-Key':apiKey()}});const d=await r.json();if(!r.ok)throw Error(d.detail||'Report failed');box.textContent='Recent posts: '+d.posts_returned+' | Likes: '+d.likes_total+' | Comments: '+d.comments_total+'\\nGrowth tips: '+(d.growth_recommendations||[]).join(' | ')+'\\n\\n'+d.posts.map(p=>p.published_at+' | Likes '+p.likes+' | Comments '+p.comments+'\\n'+p.caption+'\\n'+(p.permalink||'')).join('\\n\\n')}catch(e){box.textContent='Report not available: '+e.message}}
    async function schedule(){const out=document.getElementById('result');try{const key=document.getElementById('key').value.trim();const img=document.getElementById('img').value.trim();const when=document.getElementById('when').value;if(!key)throw Error('Enter the automation key set in Render.');if(!img.startsWith('https://'))throw Error('Use a public HTTPS image URL.');if(!when)throw Error('Choose a schedule date and time.');const response=await fetch('/api/posts/schedule',{method:'POST',headers:{'Content-Type':'application/json','X-Automation-Key':key},body:JSON.stringify({topic:document.getElementById('topic').value,caption:document.getElementById('caption').value||makeCaption(),image_url:img,instagram_user_id:document.getElementById('uid').value.trim(),scheduled_at:new Date(when).toISOString()})});const data=await response.json();if(!response.ok)throw Error(data.detail||'Schedule request failed');out.textContent='Scheduled. Post ID: '+data.post_id+'; status: '+data.status;refreshPosts()}catch(e){out.textContent='Not scheduled: '+e.message}}
    async function refreshPosts(){const box=document.getElementById('queue');try{const key=document.getElementById('key').value.trim();if(!key)throw Error('Enter the automation key first.');const response=await fetch('/api/posts',{headers:{'X-Automation-Key':key}});const data=await response.json();if(!response.ok)throw Error(data.detail||'Request failed');box.textContent=data.posts.length?data.posts.map(p=>'#'+p.id+' | '+p.status+' | '+p.scheduled_at+'\\n'+p.caption+(p.last_error?'\\nError: '+p.last_error:'')).join('\\n\\n'):'No scheduled posts.'}catch(e){box.textContent=e.message}}
    preview();</script></body></html>"""


# AI content creation, hosted image assets, Instagram reporting, and comment-reply webhook.
# Optional AI features require OPENAI_API_KEY. Image bytes are stored in PostgreSQL so Instagram
# can fetch a stable public HTTPS URL instead of a short-lived image-provider URL.
def ensure_ai_tables():
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS generated_assets (
                    asset_id UUID PRIMARY KEY,
                    image_bytes BYTEA NOT NULL,
                    mime_type TEXT NOT NULL DEFAULT 'image/png',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS handled_instagram_comments (
                    comment_id TEXT PRIMARY KEY,
                    reply_text TEXT NOT NULL,
                    handled_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        conn.commit()


def get_saved_connection(user_id: str) -> tuple[str, str]:
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE instagram_connections ADD COLUMN IF NOT EXISTS auth_method TEXT NOT NULL DEFAULT 'instagram_login'")
            cur.execute("SELECT encrypted_access_token, auth_method FROM instagram_connections WHERE instagram_user_id=%s", (user_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Instagram account is not connected with a saved token.")
    token = token_cipher().decrypt(row[0].encode("ascii")).decode("utf-8")
    return token, (row[1] or "instagram_login")


def get_saved_token(user_id: str) -> str:
    return get_saved_connection(user_id)[0]


async def openai_chat(messages: list[dict], max_tokens: int = 900) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured in Render.")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini"),
                  "messages": messages, "temperature": 0.7, "max_tokens": max_tokens},
        )
        if response.status_code >= 400:
            logger.warning("AI text generation failed with HTTP %s", response.status_code)
            raise HTTPException(status_code=502, detail="AI content generation failed. Check AI provider configuration and quota.")
        data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="AI provider returned an unexpected response.")


@app.post("/api/ai/generate")
async def generate_content(payload: dict, x_automation_key: str | None = Header(default=None)):
    require_automation_key(x_automation_key)
    topic = " ".join(str(payload.get("topic", "")).split()).strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required.")
    prompt = (
        "Create an Instagram carousel content package for the brand Kiran Kumar • AI Automation. "
        "Write in clear professional English for Indian freelancers, digital marketers and small businesses. "
        "Return exactly these sections: HOOK, SLIDE 1, SLIDE 2, SLIDE 3, SLIDE 4, CAPTION, CTA, HASHTAGS, IMAGE PROMPT. "
        "Make each slide practical, specific and mobile-readable. Avoid fabricated performance claims. "
        "Topic: " + topic
    )
    generated = await openai_chat([
        {"role": "system", "content": "You are an expert practical AI automation educator and social media content strategist."},
        {"role": "user", "content": prompt},
    ], max_tokens=1400)
    return {"ok": True, "topic": topic, "brand": "Kiran Kumar • AI Automation", "content": generated}


@app.post("/api/ai/image")
async def generate_image(payload: dict, x_automation_key: str | None = Header(default=None)):
    require_automation_key(x_automation_key)
    prompt = " ".join(str(payload.get("prompt", "")).split()).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required.")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured in Render.")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"model": os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
                      "prompt": prompt + ". Instagram-feed-safe square social media infographic, clean readable composition, practical AI automation workflow, navy and white with electric blue and cyan accents. Do not invent brand logos or tiny illegible text.",
                      "size": "1024x1024"},
            )
            if response.status_code >= 400:
                logger.warning("AI image generation failed with HTTP %s", response.status_code)
                raise HTTPException(status_code=502, detail="Image generation failed. Check provider access, model availability and quota.")
            image_data = response.json()["data"][0]
            raw = image_data.get("b64_json")
            if not raw:
                raise HTTPException(status_code=502, detail="Image provider did not return image bytes.")
            image_bytes = base64.b64decode(raw)
    except HTTPException:
        raise
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Image provider returned an unexpected response.")
    try:
        ensure_ai_tables()
        asset_id = uuid4()
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO generated_assets (asset_id, image_bytes, mime_type) VALUES (%s,%s,%s)",
                    (asset_id, image_bytes, "image/png"),
                )
            conn.commit()
        return {"ok": True, "asset_id": str(asset_id), "image_url": f"{APP_BASE_URL}/assets/{asset_id}",
                "note": "Use this public HTTPS image URL when scheduling the post."}
    except Exception:
        logger.exception("Could not store generated image asset")
        raise HTTPException(status_code=503, detail="Image generated but could not be stored. Check database configuration.")


@app.get("/assets/{asset_id}")
async def serve_generated_asset(asset_id: UUID):
    try:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT image_bytes, mime_type FROM generated_assets WHERE asset_id=%s", (asset_id,))
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image asset not found.")
        return Response(content=bytes(row[0]), media_type=row[1], headers={"Cache-Control": "public, max-age=86400"})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not serve generated image asset")
        raise HTTPException(status_code=503, detail="Image asset storage is unavailable.")


@app.get("/api/reports/instagram")
async def instagram_report(instagram_user_id: str, x_automation_key: str | None = Header(default=None)):
    require_automation_key(x_automation_key)
    token, auth_method = get_saved_connection(instagram_user_id)
    graph_url = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}" if auth_method == "facebook_login" else "https://graph.instagram.com"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{graph_url}/{instagram_user_id}/media",
            params={"fields": "id,caption,like_count,comments_count,timestamp,permalink", "limit": 25, "access_token": token},
        )
    if response.status_code >= 400:
        logger.warning("Instagram reporting request failed with HTTP %s", response.status_code)
        raise HTTPException(status_code=502, detail="Instagram reporting API failed. Check permissions and account eligibility.")
    media = response.json().get("data", [])
    report = []
    for item in media:
        report.append({
            "media_id": item.get("id"),
            "caption": (item.get("caption") or "")[:160],
            "published_at": item.get("timestamp"),
            "likes": int(item.get("like_count") or 0),
            "comments": int(item.get("comments_count") or 0),
            "permalink": item.get("permalink"),
        })
    top_post = max(report, key=lambda item: item["likes"] + item["comments"] * 2, default=None)
    recommendations = [
        "Publish consistently and compare results across at least 2–4 weeks.",
        "Use a clear save/share CTA on educational carousel posts.",
        "Reply to genuine comments promptly; keep automated replies disabled until the Meta webhook is tested.",
    ]
    if report and sum(item["comments"] for item in report) == 0:
        recommendations.append("Test a specific question in the caption to invite relevant comments.")
    if top_post:
        recommendations.append("Review the topic and format of the current highest-engagement post and create a useful follow-up.")
    return {
        "instagram_user_id": instagram_user_id,
        "posts_returned": len(report),
        "likes_total": sum(item["likes"] for item in report),
        "comments_total": sum(item["comments"] for item in report),
        "top_engagement_post": top_post,
        "growth_recommendations": recommendations,
        "posts": report,
        "note": "This report covers recent media and engagement counts, not full reach/follower analytics.",
    }


@app.get("/webhooks/instagram")
async def verify_instagram_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    verify_token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and META_WEBHOOK_VERIFY_TOKEN and secrets.compare_digest(verify_token or "", META_WEBHOOK_VERIFY_TOKEN):
        return Response(content=challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed.")


async def reply_to_instagram_comment(comment_id: str, text: str, user_id: str):
    token, auth_method = get_saved_connection(user_id)
    graph_url = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}" if auth_method == "facebook_login" else "https://graph.instagram.com"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{graph_url}/{comment_id}/replies",
            data={"message": text[:1000], "access_token": token},
        )
    if response.status_code >= 400:
        logger.warning("Instagram comment reply failed with HTTP %s", response.status_code)
        raise RuntimeError("Instagram rejected the comment reply; check comment-management permissions.")


@app.post("/webhooks/instagram")
async def receive_instagram_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not INSTAGRAM_APP_SECRET or not signature.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Webhook signature is missing or app secret is not configured.")
    expected_signature = "sha256=" + hmac.new(
        INSTAGRAM_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    if not secrets.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="Webhook signature is invalid.")
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Webhook payload is invalid JSON.")
    if not AUTO_REPLY_ENABLED:
        return {"received": True, "auto_reply_enabled": False}
    ensure_ai_tables()
    handled = 0
    for entry in body.get("entry", []):
        user_id = str(entry.get("id") or "")
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            comment_id = str(value.get("id") or value.get("comment_id") or "")
            comment_text = " ".join(str(value.get("text") or "").split()).strip()
            if not user_id or not comment_id or not comment_text:
                continue
            with database_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM handled_instagram_comments WHERE comment_id=%s", (comment_id,))
                    already_handled = cur.fetchone()
            if already_handled:
                continue
            try:
                reply = await openai_chat([
                    {"role": "system", "content": "Write one warm, short, non-spammy public Instagram reply for an AI automation education account. Do not promise results, ask for private data, or include hashtags. If the comment is abusive, political, medical, or unclear, reply politely and neutrally."},
                    {"role": "user", "content": f"Instagram comment: {comment_text}"},
                ], max_tokens=100)
                reply = reply.strip().strip('"')[:500]
                await reply_to_instagram_comment(comment_id, reply, user_id)
                with database_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO handled_instagram_comments (comment_id, reply_text) VALUES (%s,%s) ON CONFLICT DO NOTHING", (comment_id, reply))
                    conn.commit()
                handled += 1
            except Exception:
                logger.exception("Could not auto-reply to Instagram comment %s", comment_id)
    return {"received": True, "auto_replied": handled, "auto_reply_enabled": True}


@app.get("/api/automation/status")
async def automation_status():
    return {
        "service": "ok",
        "ai_text_configured": bool(OPENAI_API_KEY),
        "ai_image_configured": bool(OPENAI_API_KEY),
        "database_configured": bool(DATABASE_URL),
        "token_encryption_configured": bool(TOKEN_ENCRYPTION_KEY),
        "automation_key_configured": bool(AUTOMATION_API_KEY),
        "comment_auto_reply_enabled": AUTO_REPLY_ENABLED,
        "automatic_daily_content_enabled": AUTO_CONTENT_ENABLED,
        "automatic_daily_content_schedule": "10:00 and 18:00 Asia/Kolkata",
        "comment_auto_reply_requires": ["Meta webhook subscription", "META_WEBHOOK_VERIFY_TOKEN", "AUTO_REPLY_ENABLED=true", "OPENAI_API_KEY", "Instagram comment-management permission"],
    }


async def queue_daily_posts(instagram_user_id: str, target_date: str):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is required for automatic content creation.")
    try:
        day = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="target_date must be YYYY-MM-DD.")
    local_tz = ZoneInfo("Asia/Kolkata")
    if day <= datetime.now(local_tz).date():
        raise HTTPException(status_code=400, detail="target_date must be a future date in India time.")
    schedule_times = [
        datetime(day.year, day.month, day.day, 10, 0, tzinfo=local_tz),
        datetime(day.year, day.month, day.day, 18, 0, tzinfo=local_tz),
    ]
    topics = [
        CONTENT_TOPICS[(day.toordinal() * 2) % len(CONTENT_TOPICS)],
        CONTENT_TOPICS[(day.toordinal() * 2 + 1) % len(CONTENT_TOPICS)],
    ]
    ensure_posts_table()
    queued = []
    for topic, local_time in zip(topics, schedule_times):
        scheduled_at = local_time.astimezone(timezone.utc)
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM scheduled_posts WHERE instagram_user_id=%s AND scheduled_at=%s",
                    (instagram_user_id, scheduled_at),
                )
                existing = cur.fetchone()
        if existing:
            queued.append({"topic": topic, "post_id": existing[0], "status": "already_queued"})
            continue
        package = await generate_content({"topic": topic}, AUTOMATION_API_KEY)
        generated = package["content"]
        caption_match = re.search(r"CAPTION\s*:\s*(.*?)(?=\n(?:CTA|HASHTAGS|IMAGE PROMPT)\s*:|$)", generated, re.IGNORECASE | re.DOTALL)
        caption = caption_match.group(1).strip() if caption_match else make_caption(topic)
        caption = caption[:2000]
        prompt_match = re.search(r"IMAGE PROMPT\s*:\s*(.*?)(?=\n[A-Z][A-Z ]{2,}\s*:|$)", generated, re.IGNORECASE | re.DOTALL)
        image_prompt = prompt_match.group(1).strip() if prompt_match else f"Instagram infographic about {topic}"
        image_data = await generate_image({"prompt": image_prompt}, AUTOMATION_API_KEY)
        result = await schedule_post({
            "topic": topic,
            "caption": caption,
            "image_url": image_data["image_url"],
            "instagram_user_id": instagram_user_id,
            "scheduled_at": scheduled_at.isoformat(),
        }, AUTOMATION_API_KEY)
        queued.append({"topic": topic, "post_id": result["post_id"], "status": result["status"], "scheduled_at": result["scheduled_at"]})
    return {"ok": True, "target_date": target_date, "posts": queued}


@app.post("/api/automation/queue-daily")
async def queue_daily_endpoint(payload: dict, x_automation_key: str | None = Header(default=None)):
    require_automation_key(x_automation_key)
    user_id = str(payload.get("instagram_user_id") or INSTAGRAM_USER_ID).strip()
    target_date = str(payload.get("target_date") or (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=1)).isoformat())
    if not user_id:
        raise HTTPException(status_code=400, detail="instagram_user_id is required or configure INSTAGRAM_USER_ID.")
    return await queue_daily_posts(user_id, target_date)


async def maybe_queue_daily_content():
    if not AUTO_CONTENT_ENABLED or not INSTAGRAM_USER_ID or not DATABASE_URL or not TOKEN_ENCRYPTION_KEY or not AUTOMATION_API_KEY or not OPENAI_API_KEY:
        return
    tomorrow = datetime.now(ZoneInfo("Asia/Kolkata")).date() + __import__("datetime").timedelta(days=1)
    target_date = tomorrow.isoformat()
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS automation_daily_batches (
                    target_date DATE NOT NULL,
                    instagram_user_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'processing',
                    last_error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (target_date, instagram_user_id)
                )
            """)
            cur.execute("ALTER TABLE automation_daily_batches ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'processing'")
            cur.execute("ALTER TABLE automation_daily_batches ADD COLUMN IF NOT EXISTS last_error TEXT")
            cur.execute(
                "INSERT INTO automation_daily_batches (target_date, instagram_user_id, status) VALUES (%s,%s,'processing') ON CONFLICT DO NOTHING RETURNING target_date",
                (tomorrow, INSTAGRAM_USER_ID),
            )
            claimed = cur.fetchone()
        conn.commit()
    if not claimed:
        return
    try:
        await queue_daily_posts(INSTAGRAM_USER_ID, target_date)
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE automation_daily_batches SET status='completed', last_error=NULL WHERE target_date=%s AND instagram_user_id=%s", (tomorrow, INSTAGRAM_USER_ID))
            conn.commit()
    except Exception as exc:
        with database_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE automation_daily_batches SET status='failed', last_error=%s WHERE target_date=%s AND instagram_user_id=%s", (str(exc)[:500], tomorrow, INSTAGRAM_USER_ID))
            conn.commit()
        raise


from app.studio import router as studio_router
app.include_router(studio_router)

# Expose authenticated remote MCP tools from the same app entry point used by existing deployments.
from app.mcp_server import mount_mcp
mount_mcp(app)


# Metricool-style mobile dashboard for content creation, scheduling and reporting.
from app.dashboard import router as dashboard_router
app.include_router(dashboard_router)
