"""Pinterest OAuth and image-pin publishing for SocialPilot AI."""
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

router = APIRouter(tags=["pinterest"])
CLIENT_ID = os.getenv("PINTEREST_APP_ID", "").strip()
CLIENT_SECRET = os.getenv("PINTEREST_APP_SECRET", "").strip()
BASE_URL = os.getenv("APP_BASE_URL", "https://socialpilot-ai-mvp.onrender.com").strip().rstrip("/")
REDIRECT_URI = os.getenv("PINTEREST_REDIRECT_URI", BASE_URL + "/auth/pinterest/callback").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
SCOPES = "user_accounts:read,pins:read,pins:write"

def db():
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured.")
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
    return psycopg.connect(url, connect_timeout=10)

def workspace_for(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE, "")
    session = _read_session(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="Log in at /account before connecting Pinterest.")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT w.id FROM customer_workspaces w JOIN customer_accounts a ON a.id=w.owner_account_id WHERE a.id=%s AND a.is_active=TRUE", (session["sub"],))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Customer workspace not found or disabled.")
    return str(row[0])

def ensure_tables(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS pinterest_oauth_states (state_hash TEXT PRIMARY KEY, workspace_id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
    cur.execute("CREATE TABLE IF NOT EXISTS social_connections (id BIGSERIAL PRIMARY KEY, workspace_id UUID NOT NULL, platform TEXT NOT NULL, provider_user_id TEXT NOT NULL, display_name TEXT, encrypted_access_token TEXT NOT NULL, expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(workspace_id, platform, provider_user_id))")
    cur.execute("ALTER TABLE social_connections ADD COLUMN IF NOT EXISTS encrypted_refresh_token TEXT")

def encrypt(value: str) -> str:
    if not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured.")
    return Fernet(ENCRYPTION_KEY.encode("ascii")).encrypt(value.encode()).decode("ascii")

@router.get("/auth/pinterest/start")
async def pinterest_start(request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Set PINTEREST_APP_ID and PINTEREST_APP_SECRET in Render Environment.")
    workspace_id = workspace_for(request)
    state = secrets.token_urlsafe(32)
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM pinterest_oauth_states WHERE created_at < NOW() - INTERVAL '15 minutes'")
            cur.execute("INSERT INTO pinterest_oauth_states(state_hash,workspace_id) VALUES (%s,%s)", (hashlib.sha256(state.encode()).hexdigest(), workspace_id))
        conn.commit()
    params = {"client_id":CLIENT_ID,"redirect_uri":REDIRECT_URI,"response_type":"code","scope":SCOPES,"state":state}
    return RedirectResponse("https://www.pinterest.com/oauth/?" + urlencode(params), status_code=302)

@router.get("/auth/pinterest/callback")
async def pinterest_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"connected":False,"platform":"pinterest","error":"Pinterest authorization was denied or cancelled."})
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing Pinterest OAuth code/state.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM pinterest_oauth_states WHERE state_hash=%s AND created_at >= NOW() - INTERVAL '15 minutes' RETURNING workspace_id", (hashlib.sha256(state.encode()).hexdigest(),))
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=400, detail="Pinterest OAuth state is invalid, expired, or already used.")
    if not CLIENT_ID or not CLIENT_SECRET or not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="Pinterest credentials or TOKEN_ENCRYPTION_KEY are not configured.")
    workspace_id = str(row[0])
    async with httpx.AsyncClient(timeout=25) as client:
        token_response = await client.post("https://api.pinterest.com/v5/oauth/token", data={"grant_type":"authorization_code","code":code,"redirect_uri":REDIRECT_URI}, auth=(CLIENT_ID,CLIENT_SECRET), headers={"Content-Type":"application/x-www-form-urlencoded"})
        if token_response.is_error:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"pinterest","step":"token_exchange","http_status":token_response.status_code,"error":"Pinterest token exchange failed; verify callback URL and app access."})
        token_data = token_response.json()
        access = token_data.get("access_token")
        if not access:
            raise HTTPException(status_code=502, detail="Pinterest did not return an access token.")
        profile = await client.get("https://api.pinterest.com/v5/user_account", headers={"Authorization":"Bearer "+access})
        if profile.is_error:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"pinterest","step":"profile_lookup","http_status":profile.status_code,"error":"Pinterest profile lookup failed; check user_accounts:read scope."})
        user = profile.json()
    account_id = str(user.get("username") or user.get("id") or "")
    if not account_id:
        raise HTTPException(status_code=502, detail="Pinterest account identifier missing.")
    expires_in = int(token_data.get("expires_in") or 0)
    refresh = token_data.get("refresh_token")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("""INSERT INTO social_connections(workspace_id,platform,provider_user_id,display_name,encrypted_access_token,encrypted_refresh_token,expires_at)
                VALUES (%s,'pinterest',%s,%s,%s,%s,CASE WHEN %s>0 THEN NOW()+(%s*INTERVAL '1 second') ELSE NULL END)
                ON CONFLICT(workspace_id,platform,provider_user_id) DO UPDATE SET display_name=EXCLUDED.display_name,encrypted_access_token=EXCLUDED.encrypted_access_token,encrypted_refresh_token=COALESCE(EXCLUDED.encrypted_refresh_token,social_connections.encrypted_refresh_token),expires_at=EXCLUDED.expires_at,updated_at=NOW()""",
                (workspace_id,account_id,str(user.get("username") or "Pinterest account"),encrypt(access),encrypt(refresh) if refresh else None,expires_in,expires_in))
        conn.commit()
    return RedirectResponse(BASE_URL + "/platforms?pinterest=connected", status_code=303)

class PinInput(BaseModel):
    board_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=800)
    image_url: HttpUrl
    link: HttpUrl | None = None

@router.post("/api/pinterest/pins")
async def publish_pin(payload: PinInput, request: Request):
    workspace_id = workspace_for(request)
    if not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured.")
    parsed = urlparse(str(payload.image_url))
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Pinterest image_url must be a public HTTPS URL.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("SELECT provider_user_id,encrypted_access_token,encrypted_refresh_token,expires_at FROM social_connections WHERE workspace_id=%s AND platform='pinterest' ORDER BY updated_at DESC LIMIT 1", (workspace_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=409, detail="Connect Pinterest first at /auth/pinterest/start.")
    provider_user_id = row[0]
    access = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[1].encode("ascii")).decode()
    refresh = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[2].encode("ascii")).decode() if row[2] else None
    if row[3] and row[3].timestamp() <= time.time():
        if not refresh:
            raise HTTPException(status_code=409, detail="Pinterest token expired; reconnect Pinterest.")
        async with httpx.AsyncClient(timeout=25) as client:
            tr = await client.post("https://api.pinterest.com/v5/oauth/token", data={"grant_type":"refresh_token","refresh_token":refresh}, auth=(CLIENT_ID,CLIENT_SECRET), headers={"Content-Type":"application/x-www-form-urlencoded"})
            if tr.is_error:
                raise HTTPException(status_code=502, detail="Pinterest token refresh failed; reconnect Pinterest.")
            td = tr.json()
        access = td["access_token"]
        new_refresh = td.get("refresh_token", refresh)
        exp = int(td.get("expires_in") or 0)
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE social_connections SET encrypted_access_token=%s,encrypted_refresh_token=%s,expires_at=CASE WHEN %s>0 THEN NOW()+(%s*INTERVAL '1 second') ELSE NULL END,updated_at=NOW() WHERE workspace_id=%s AND platform='pinterest' AND provider_user_id=%s", (encrypt(access),encrypt(new_refresh),exp,exp,workspace_id,provider_user_id))
            conn.commit()
    body = {"board_id":payload.board_id,"title":payload.title,"description":payload.description,"media_source":{"source_type":"image_url","url":str(payload.image_url)}}
    if payload.link:
        body["link"] = str(payload.link)
    async with httpx.AsyncClient(timeout=35) as client:
        resp = await client.post("https://api.pinterest.com/v5/pins", json=body, headers={"Authorization":"Bearer "+access,"Content-Type":"application/json"})
    if resp.is_error:
        raise HTTPException(status_code=502, detail={"message":"Pinterest rejected the pin. Check board ownership, media URL, app permissions and API access.","provider_status":resp.status_code})
    data = resp.json()
    return {"published":True,"platform":"pinterest","pin_id":data.get("id"),"title":payload.title}
