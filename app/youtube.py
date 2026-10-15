"""YouTube Google OAuth connection for SocialPilot AI."""
import hashlib
import os
import secrets
import time
from urllib.parse import urlencode

import httpx
import psycopg
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse
from app.customer_auth import SESSION_COOKIE, _read_session

router = APIRouter(tags=["youtube"])
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
BASE_URL = os.getenv("APP_BASE_URL", "https://socialpilot-ai-mvp.onrender.com").strip().rstrip("/")
REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", BASE_URL + "/auth/youtube/callback").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()

def db():
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured.")
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
    return psycopg.connect(url, connect_timeout=10)

def workspace_for(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE, "")
    session = _read_session(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="Log in at /account before connecting YouTube.")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT w.id FROM customer_workspaces w JOIN customer_accounts a ON a.id=w.owner_account_id WHERE a.id=%s AND a.is_active=TRUE", (session["sub"],))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Customer workspace not found or disabled.")
    return str(row[0])

def ensure_tables(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS youtube_oauth_states (state_hash TEXT PRIMARY KEY, workspace_id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
    cur.execute("CREATE TABLE IF NOT EXISTS social_connections (id BIGSERIAL PRIMARY KEY, workspace_id UUID NOT NULL, platform TEXT NOT NULL, provider_user_id TEXT NOT NULL, display_name TEXT, encrypted_access_token TEXT NOT NULL, expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(workspace_id, platform, provider_user_id))")

@router.get("/auth/youtube/start")
async def youtube_start(request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Render Environment.")
    workspace_id = workspace_for(request)
    state = secrets.token_urlsafe(32)
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM youtube_oauth_states WHERE created_at < NOW() - INTERVAL '15 minutes'")
            cur.execute("INSERT INTO youtube_oauth_states(state_hash, workspace_id) VALUES (%s,%s)", (hashlib.sha256(state.encode()).hexdigest(), workspace_id))
        conn.commit()
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
        "state": state,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params), status_code=302)

@router.get("/auth/youtube/callback")
async def youtube_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"connected": False, "platform": "youtube", "error": "Google authorization was denied or cancelled."})
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing YouTube OAuth code/state.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM youtube_oauth_states WHERE state_hash=%s AND created_at >= NOW() - INTERVAL '15 minutes' RETURNING workspace_id", (hashlib.sha256(state.encode()).hexdigest(),))
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=400, detail="YouTube OAuth state is invalid, expired, or already used.")
    if not CLIENT_ID or not CLIENT_SECRET or not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="Google credentials or TOKEN_ENCRYPTION_KEY are not configured.")
    async with httpx.AsyncClient(timeout=25) as client:
        token_response = await client.post("https://oauth2.googleapis.com/token", data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        })
        if token_response.is_error:
            return JSONResponse(status_code=502, content={"connected": False, "platform": "youtube", "step": "token_exchange", "http_status": token_response.status_code, "error": "Google token exchange failed. Check redirect URI, OAuth consent and credentials."})
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="Google did not return an access token.")
        channel_response = await client.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"}, headers={"Authorization": "Bearer " + access_token})
        if channel_response.is_error:
            return JSONResponse(status_code=502, content={"connected": False, "platform": "youtube", "step": "channel_lookup", "http_status": channel_response.status_code, "error": "YouTube channel lookup failed. Enable YouTube Data API v3 and check OAuth scopes."})
        data = channel_response.json()
    items = data.get("items") or []
    if not items:
        raise HTTPException(status_code=409, detail="Google account is authorized but no YouTube channel was returned.")
    channel = items[0]
    channel_id = str(channel.get("id") or "")
    title = str((channel.get("snippet") or {}).get("title") or "YouTube channel")
    if not channel_id:
        raise HTTPException(status_code=502, detail="YouTube channel ID missing.")
    encrypted = Fernet(ENCRYPTION_KEY.encode("ascii")).encrypt(access_token.encode()).decode("ascii")
    expires_in = int(token_data.get("expires_in") or 0)
    refresh_token = token_data.get("refresh_token")
    if refresh_token:
        encrypted_refresh = Fernet(ENCRYPTION_KEY.encode("ascii")).encrypt(refresh_token.encode()).decode("ascii")
        with db() as conn:
            with conn.cursor() as cur:
                ensure_tables(cur)
                cur.execute("ALTER TABLE social_connections ADD COLUMN IF NOT EXISTS encrypted_refresh_token TEXT")
                cur.execute("""INSERT INTO social_connections(workspace_id,platform,provider_user_id,display_name,encrypted_access_token,encrypted_refresh_token,expires_at)
                    VALUES (%s,'youtube',%s,%s,%s,%s,CASE WHEN %s > 0 THEN NOW() + (%s * INTERVAL '1 second') ELSE NULL END)
                    ON CONFLICT(workspace_id,platform,provider_user_id) DO UPDATE SET display_name=EXCLUDED.display_name,encrypted_access_token=EXCLUDED.encrypted_access_token,encrypted_refresh_token=EXCLUDED.encrypted_refresh_token,expires_at=EXCLUDED.expires_at,updated_at=NOW()""",
                    (str(row[0]), channel_id, title, encrypted, encrypted_refresh, expires_in, expires_in))
            conn.commit()
    else:
        with db() as conn:
            with conn.cursor() as cur:
                ensure_tables(cur)
                cur.execute("ALTER TABLE social_connections ADD COLUMN IF NOT EXISTS encrypted_refresh_token TEXT")
                cur.execute("""INSERT INTO social_connections(workspace_id,platform,provider_user_id,display_name,encrypted_access_token,expires_at)
                    VALUES (%s,'youtube',%s,%s,%s,CASE WHEN %s > 0 THEN NOW() + (%s * INTERVAL '1 second') ELSE NULL END)
                    ON CONFLICT(workspace_id,platform,provider_user_id) DO UPDATE SET display_name=EXCLUDED.display_name,encrypted_access_token=EXCLUDED.encrypted_access_token,expires_at=EXCLUDED.expires_at,updated_at=NOW()""",
                    (str(row[0]), channel_id, title, encrypted, expires_in, expires_in))
            conn.commit()
    return RedirectResponse(BASE_URL + "/platforms?youtube=connected", status_code=303)


@router.post("/api/youtube/videos")
async def upload_youtube_video(
    request: Request,
    video: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=100),
    description: str = Form(default="", max_length=5000),
    privacy_status: str = Form(default="private", pattern="^(private|unlisted|public)$"),
):
    """Upload a video using YouTube's resumable upload API; starts private by default."""
    workspace_id = workspace_for(request)
    if not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured.")
    content_type = (video.content_type or "").lower()
    if not content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Upload a video file with a video/* content type.")
    video.file.seek(0, 2)
    size = video.file.tell()
    video.file.seek(0)
    max_size = 256 * 1024 * 1024
    if size <= 0 or size > max_size:
        raise HTTPException(status_code=413, detail="Video must be between 1 byte and 256 MB.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("ALTER TABLE social_connections ADD COLUMN IF NOT EXISTS encrypted_refresh_token TEXT")
            cur.execute("SELECT provider_user_id,encrypted_access_token,encrypted_refresh_token,expires_at FROM social_connections WHERE workspace_id=%s AND platform='youtube' ORDER BY updated_at DESC LIMIT 1", (workspace_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=409, detail="Connect YouTube first at /auth/youtube/start.")
    channel_id = str(row[0])
    access = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[1].encode("ascii")).decode()
    refresh = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[2].encode("ascii")).decode() if row[2] else None
    if row[3] and row[3].timestamp() <= time.time():
        if not refresh:
            raise HTTPException(status_code=409, detail="Google access token expired; reconnect YouTube and grant offline access.")
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post("https://oauth2.googleapis.com/token", data={"grant_type":"refresh_token","refresh_token":refresh,"client_id":CLIENT_ID,"client_secret":CLIENT_SECRET})
            if token_response.is_error:
                raise HTTPException(status_code=502, detail="Google token refresh failed; reconnect YouTube.")
            td = token_response.json()
        access = td["access_token"]
        expires = int(td.get("expires_in") or 0)
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE social_connections SET encrypted_access_token=%s,expires_at=CASE WHEN %s>0 THEN NOW()+(%s*INTERVAL '1 second') ELSE NULL END,updated_at=NOW() WHERE workspace_id=%s AND platform='youtube' AND provider_user_id=%s", (Fernet(ENCRYPTION_KEY.encode("ascii")).encrypt(access.encode()).decode("ascii"),expires,expires,workspace_id,channel_id))
            conn.commit()
    metadata = {"snippet":{"title":title,"description":description},"status":{"privacyStatus":privacy_status}}
    async with httpx.AsyncClient(timeout=60) as client:
        init = await client.post(
            "https://www.googleapis.com/upload/youtube/v3/videos",
            params={"uploadType":"resumable","part":"snippet,status"},
            json=metadata,
            headers={"Authorization":"Bearer "+access,"Content-Type":"application/json; charset=UTF-8","X-Upload-Content-Type":content_type,"X-Upload-Content-Length":str(size)},
        )
        if init.is_error or not init.headers.get("location"):
            raise HTTPException(status_code=502, detail={"message":"YouTube upload session could not be created. Check YouTube Data API v3, upload scope and quota.","provider_status":init.status_code})
        upload_url = init.headers["location"]
        async def chunks():
            while True:
                chunk = await video.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
        uploaded = await client.put(upload_url, content=chunks(), headers={"Content-Type":content_type,"Content-Length":str(size)})
    if uploaded.is_error:
        raise HTTPException(status_code=502, detail={"message":"YouTube rejected the video upload. Check quota, channel eligibility, file format and API access.","provider_status":uploaded.status_code})
    data = uploaded.json()
    return {"uploaded":True,"platform":"youtube","video_id":data.get("id"),"privacy_status":(data.get("status") or {}).get("privacyStatus"),"message":"YouTube returned a video ID. Verify processing status in YouTube Studio before sharing publicly."}
