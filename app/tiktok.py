"""TikTok OAuth and URL-based video publishing for SocialPilot AI."""
import hashlib
import os
import secrets
import time
from urllib.parse import urlencode, urlparse

import httpx
import psycopg
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, HttpUrl
from app.customer_auth import SESSION_COOKIE, _read_session

router = APIRouter(tags=["tiktok"])
CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "").strip()
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "").strip()
BASE_URL = os.getenv("APP_BASE_URL", "https://socialpilot-ai-mvp.onrender.com").strip().rstrip("/")
REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", BASE_URL + "/auth/tiktok/callback").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
SCOPES = "user.info.basic,video.publish,video.upload"

def db():
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured.")
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
    return psycopg.connect(url, connect_timeout=10)

def workspace_for(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE, "")
    session = _read_session(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="Log in at /account before connecting TikTok.")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT w.id FROM customer_workspaces w JOIN customer_accounts a ON a.id=w.owner_account_id WHERE a.id=%s AND a.is_active=TRUE", (session["sub"],))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Customer workspace not found or disabled.")
    return str(row[0])

def ensure_tables(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS tiktok_oauth_states (state_hash TEXT PRIMARY KEY, workspace_id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
    cur.execute("CREATE TABLE IF NOT EXISTS social_connections (id BIGSERIAL PRIMARY KEY, workspace_id UUID NOT NULL, platform TEXT NOT NULL, provider_user_id TEXT NOT NULL, display_name TEXT, encrypted_access_token TEXT NOT NULL, expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(workspace_id, platform, provider_user_id))")
    cur.execute("ALTER TABLE social_connections ADD COLUMN IF NOT EXISTS encrypted_refresh_token TEXT")

def encrypt(value: str) -> str:
    if not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured.")
    return Fernet(ENCRYPTION_KEY.encode("ascii")).encrypt(value.encode()).decode("ascii")

@router.get("/auth/tiktok/start")
async def tiktok_start(request: Request):
    if not CLIENT_KEY or not CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in Render Environment.")
    workspace_id = workspace_for(request)
    state = secrets.token_urlsafe(32)
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM tiktok_oauth_states WHERE created_at < NOW() - INTERVAL '15 minutes'")
            cur.execute("INSERT INTO tiktok_oauth_states(state_hash,workspace_id) VALUES (%s,%s)", (hashlib.sha256(state.encode()).hexdigest(), workspace_id))
        conn.commit()
    params = {"client_key":CLIENT_KEY,"response_type":"code","scope":SCOPES,"redirect_uri":REDIRECT_URI,"state":state}
    return RedirectResponse("https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params), status_code=302)

@router.get("/auth/tiktok/callback")
async def tiktok_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"connected":False,"platform":"tiktok","error":"TikTok authorization was denied or cancelled."})
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing TikTok OAuth code/state.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM tiktok_oauth_states WHERE state_hash=%s AND created_at >= NOW() - INTERVAL '15 minutes' RETURNING workspace_id", (hashlib.sha256(state.encode()).hexdigest(),))
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=400, detail="TikTok OAuth state is invalid, expired, or already used.")
    if not CLIENT_KEY or not CLIENT_SECRET or not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TikTok credentials or TOKEN_ENCRYPTION_KEY are not configured.")
    workspace_id = str(row[0])
    async with httpx.AsyncClient(timeout=25) as client:
        tr = await client.post("https://open.tiktokapis.com/v2/oauth/token/", data={"client_key":CLIENT_KEY,"client_secret":CLIENT_SECRET,"code":code,"grant_type":"authorization_code","redirect_uri":REDIRECT_URI}, headers={"Content-Type":"application/x-www-form-urlencoded"})
        if tr.is_error:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"tiktok","step":"token_exchange","http_status":tr.status_code,"error":"TikTok token exchange failed; check app configuration and redirect URI."})
        token_data = tr.json().get("data") or {}
        access = token_data.get("access_token")
        if not access:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"tiktok","error":"TikTok did not return an access token."})
        profile_response = await client.get("https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name", headers={"Authorization":"Bearer "+access})
        if profile_response.is_error:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"tiktok","step":"profile_lookup","http_status":profile_response.status_code,"error":"TikTok profile lookup failed; check user.info.basic scope."})
        user = (profile_response.json().get("data") or {}).get("user") or {}
    user_id = str(user.get("open_id") or "")
    display = str(user.get("display_name") or "TikTok account")
    if not user_id:
        raise HTTPException(status_code=502, detail="TikTok open_id was not returned.")
    expires = int(token_data.get("expires_in") or 0)
    refresh = token_data.get("refresh_token")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("""INSERT INTO social_connections(workspace_id,platform,provider_user_id,display_name,encrypted_access_token,encrypted_refresh_token,expires_at)
                VALUES (%s,'tiktok',%s,%s,%s,%s,CASE WHEN %s>0 THEN NOW()+(%s*INTERVAL '1 second') ELSE NULL END)
                ON CONFLICT(workspace_id,platform,provider_user_id) DO UPDATE SET display_name=EXCLUDED.display_name,encrypted_access_token=EXCLUDED.encrypted_access_token,encrypted_refresh_token=COALESCE(EXCLUDED.encrypted_refresh_token,social_connections.encrypted_refresh_token),expires_at=EXCLUDED.expires_at,updated_at=NOW()""",
                (workspace_id,user_id,display,encrypt(access),encrypt(refresh) if refresh else None,expires,expires))
        conn.commit()
    return RedirectResponse(BASE_URL + "/platforms?tiktok=connected", status_code=303)

class TikTokVideoInput(BaseModel):
    video_url: HttpUrl
    title: str = Field(min_length=1, max_length=2200)
    privacy_level: str = Field(default="SELF_ONLY", pattern="^(PUBLIC_TO_EVERYONE|MUTUAL_FOLLOW_FRIENDS|FOLLOWER_OF_CREATOR|SELF_ONLY)$")
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False

@router.post("/api/tiktok/videos")
async def publish_tiktok_video(payload: TikTokVideoInput, request: Request):
    workspace_id = workspace_for(request)
    if not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured.")
    if urlparse(str(payload.video_url)).scheme != "https":
        raise HTTPException(status_code=422, detail="TikTok video_url must be public HTTPS.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("SELECT provider_user_id,encrypted_access_token,encrypted_refresh_token,expires_at FROM social_connections WHERE workspace_id=%s AND platform='tiktok' ORDER BY updated_at DESC LIMIT 1", (workspace_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=409, detail="Connect TikTok first at /auth/tiktok/start.")
    provider_user_id = row[0]
    access = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[1].encode("ascii")).decode()
    refresh = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[2].encode("ascii")).decode() if row[2] else None
    if row[3] and row[3].timestamp() <= time.time():
        if not refresh:
            raise HTTPException(status_code=409, detail="TikTok token expired; reconnect TikTok.")
        async with httpx.AsyncClient(timeout=25) as client:
            tr = await client.post("https://open.tiktokapis.com/v2/oauth/token/", data={"client_key":CLIENT_KEY,"client_secret":CLIENT_SECRET,"grant_type":"refresh_token","refresh_token":refresh}, headers={"Content-Type":"application/x-www-form-urlencoded"})
            if tr.is_error:
                raise HTTPException(status_code=502, detail="TikTok token refresh failed; reconnect TikTok.")
            td = tr.json().get("data") or {}
        access = td["access_token"]
        new_refresh = td.get("refresh_token", refresh)
        exp = int(td.get("expires_in") or 0)
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE social_connections SET encrypted_access_token=%s,encrypted_refresh_token=%s,expires_at=CASE WHEN %s>0 THEN NOW()+(%s*INTERVAL '1 second') ELSE NULL END,updated_at=NOW() WHERE workspace_id=%s AND platform='tiktok' AND provider_user_id=%s", (encrypt(access),encrypt(new_refresh),exp,exp,workspace_id,provider_user_id))
            conn.commit()
    body = {"post_info":{"title":payload.title,"privacy_level":payload.privacy_level,"disable_comment":payload.disable_comment,"disable_duet":payload.disable_duet,"disable_stitch":payload.disable_stitch},"source_info":{"source":"PULL_FROM_URL","video_url":str(payload.video_url)}}
    async with httpx.AsyncClient(timeout=35) as client:
        resp = await client.post("https://open.tiktokapis.com/v2/post/publish/video/init/", json=body, headers={"Authorization":"Bearer "+access,"Content-Type":"application/json; charset=UTF-8"})
    if resp.is_error:
        raise HTTPException(status_code=502, detail={"message":"TikTok rejected the video. Check Content Posting API approval, verified URL domain, privacy options and account eligibility.","provider_status":resp.status_code})
    data = resp.json().get("data") or {}
    return {"accepted":True,"platform":"tiktok","publish_id":data.get("publish_id"),"message":"TikTok accepted the publish request. Check status before claiming the video is live."}
