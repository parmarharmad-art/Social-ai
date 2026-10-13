import logging
import os
import secrets
from urllib.parse import urlencode

import httpx
import psycopg
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

load_dotenv()

app = FastAPI(title="SocialPilot AI MVP", version="0.2.0")
logger = logging.getLogger(__name__)

INSTAGRAM_APP_ID = (os.getenv("INSTAGRAM_APP_ID") or os.getenv("META_APP_ID") or "1559704026184551").strip()
INSTAGRAM_APP_SECRET = (os.getenv("INSTAGRAM_APP_SECRET") or os.getenv("META_APP_SECRET") or "").strip()
REDIRECT_URI = os.getenv(
    "INSTAGRAM_REDIRECT_URI",
    "https://socialpilot-ai-mvp.onrender.com/auth/instagram/callback",
).strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()

oauth_states: dict[str, str] = {}


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


def save_encrypted_token(user_id: str, access_token: str, expires_in: int | None):
    encrypted = token_cipher().encrypt(access_token.encode("utf-8")).decode("ascii")
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS instagram_connections (
                    instagram_user_id TEXT PRIMARY KEY,
                    encrypted_access_token TEXT NOT NULL,
                    token_expires_in BIGINT,
                    connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                INSERT INTO instagram_connections
                    (instagram_user_id, encrypted_access_token, token_expires_in)
                VALUES (%s, %s, %s)
                ON CONFLICT (instagram_user_id) DO UPDATE SET
                    encrypted_access_token = EXCLUDED.encrypted_access_token,
                    token_expires_in = EXCLUDED.token_expires_in,
                    updated_at = NOW()
            """, (user_id, encrypted, expires_in))
        conn.commit()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SocialPilot AI</title><style>body{font:16px system-ui;max-width:760px;margin:40px auto;padding:0 18px;color:#18212f}
    .card{border:1px solid #d9e0e8;border-radius:16px;padding:22px}a{display:inline-block;background:#1769e0;color:white;padding:12px 16px;border-radius:9px;text-decoration:none}</style></head>
    <body><div class="card"><h1>SocialPilot AI</h1><p>Instagram Creator account connection.</p>
    <p><a href="/auth/instagram/start">Connect Instagram</a></p>
    <p>Encrypted token storage requires DATABASE_URL and TOKEN_ENCRYPTION_KEY configuration.</p></div></body></html>
    """


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
    oauth_states[state] = REDIRECT_URI
    params = {
        "client_id": INSTAGRAM_APP_ID,
        "redirect_uri": oauth_states[state],
        "response_type": "code",
        "scope": "instagram_business_basic,instagram_business_content_publish",
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
    exchange_redirect_uri = oauth_states.pop(state)
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
            return JSONResponse(status_code=502, content={
                "connected": False,
                "message": "Instagram login succeeded but long-lived token exchange failed. Check Meta API configuration.",
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
        save_encrypted_token(instagram_user_id, long_token, expires_in)
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
        "message": "Instagram connected and token stored encrypted. Publishing automation still needs implementation and testing.",
        "user_id": instagram_user_id,
        "expires_in": expires_in,
    }
