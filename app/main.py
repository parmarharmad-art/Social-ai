import logging
import os
import secrets
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

load_dotenv()

app = FastAPI(title="SocialPilot AI MVP", version="0.1.0")
logger = logging.getLogger(__name__)

# Instagram Business Login uses the Instagram app ID shown under the Instagram product.
# Configure INSTAGRAM_APP_SECRET securely in Render; never commit the secret.
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID", "1559704026184551").strip()
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "").strip()
REDIRECT_URI = os.getenv(
    "INSTAGRAM_REDIRECT_URI",
    "https://socialpilot-ai-mvp.onrender.com/auth/instagram/callback",
).strip()

# In-memory state is suitable only for a local smoke test. Use a secure,
# persistent session store before deployment or multi-user use.
oauth_states: set[str] = set()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!doctype html>
    <html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SocialPilot AI</title>
    <style>
      body{font:16px system-ui;max-width:760px;margin:40px auto;padding:0 18px;color:#18212f}
      .card{border:1px solid #d9e0e8;border-radius:16px;padding:22px}
      a{display:inline-block;background:#1769e0;color:white;padding:12px 16px;border-radius:9px;text-decoration:none}
      small{color:#526174}
    </style></head><body><div class="card">
    <h1>SocialPilot AI</h1>
    <p>Instagram Creator account connection — starter dashboard.</p>
    <p><a href="/auth/instagram/start">Connect Instagram</a></p>
    <p><small>Connection and publishing are not considered active until Meta OAuth has been configured and tested.</small></p>
    </div></body></html>
    """


@app.get("/health")
async def health():
    return {"status": "ok", "service": "socialpilot-ai-mvp"}


@app.get("/diagnostics/oauth-config")
async def oauth_config_check():
    # Safe diagnostics only: never return the app secret or any access token.
    return {
        "instagram_app_id": INSTAGRAM_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "secret_configured": bool(INSTAGRAM_APP_SECRET),
    }


@app.get("/auth/instagram/start")
async def instagram_start():
    if not INSTAGRAM_APP_ID or not REDIRECT_URI:
        raise HTTPException(
            status_code=503,
            detail="Setup required: configure INSTAGRAM_APP_ID and INSTAGRAM_REDIRECT_URI in the server environment.",
        )

    state = secrets.token_urlsafe(32)
    oauth_states.add(state)
    params = {
        "client_id": INSTAGRAM_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "instagram_business_basic,instagram_business_content_publish",
        "state": state,
    }
    return RedirectResponse(
        "https://www.instagram.com/oauth/authorize?" + urlencode(params),
        status_code=302,
    )


@app.get("/auth/instagram/callback")
async def instagram_callback(request: Request, code: str | None = None,
                             state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(
            status_code=400,
            content={"connected": False, "error": "Instagram authorization was cancelled or denied."},
        )
    if not code or not state or state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    oauth_states.discard(state)

    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET or not REDIRECT_URI:
        raise HTTPException(status_code=503, detail="Instagram OAuth environment is not configured.")

    # Exchange the authorization code for a short-lived Instagram user token.
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": INSTAGRAM_APP_ID,
                "client_secret": INSTAGRAM_APP_SECRET,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
                "code": code,
            },
        )
        if response.status_code >= 400:
            # Log only Meta's non-secret error fields. Never log the OAuth code,
            # app secret, request form, or any access token.
            try:
                meta_error = response.json().get("error", {})
                if not isinstance(meta_error, dict):
                    meta_error = {}
            except ValueError:
                meta_error = {}
            logger.warning(
                "Instagram token exchange rejected: http_status=%s error_type=%s error_code=%s error_message=%s",
                response.status_code,
                meta_error.get("type", "unknown"),
                meta_error.get("code", "unknown"),
                str(meta_error.get("message", "No error message returned"))[:300],
            )
            return JSONResponse(
                status_code=502,
                content={
                    "connected": False,
                    "error": "Instagram token exchange failed.",
                    "meta_http_status": response.status_code,
                    "meta_error_type": meta_error.get("type"),
                    "meta_error_code": meta_error.get("code"),
                    "meta_error_message": str(meta_error.get("message", "No error message returned"))[:300],
                },
            )
        token_data = response.json()

        short_token = token_data.get("access_token")
        if not short_token:
            raise HTTPException(status_code=502, detail="Instagram did not return an access token.")

        # Exchange for a long-lived token; do not expose the token in the browser.
        long_response = await client.get(
            "https://graph.instagram.com/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": INSTAGRAM_APP_SECRET,
                "access_token": short_token,
            },
        )
        if long_response.status_code >= 400:
            return JSONResponse(
                status_code=502,
                content={"connected": False, "message": "Login succeeded but long-lived token exchange failed. Check Meta API configuration."},
            )

    # Deliberately do not persist tokens in this starter. Add encrypted storage before production.
    return {
        "connected": True,
        "message": "Instagram OAuth succeeded. Token was not saved; secure token storage must be implemented before automation.",
        "user_id": token_data.get("user_id"),
        "expires_in": long_response.json().get("expires_in"),
    }
