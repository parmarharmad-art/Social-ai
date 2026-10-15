"""X (Twitter) OAuth 2.0 PKCE and text publishing for SocialPilot AI."""
import base64
import hashlib
import os
import secrets
import time
from urllib.parse import urlencode

import httpx
import psycopg
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from app.customer_auth import SESSION_COOKIE, _read_session

router = APIRouter(tags=["x"])
CLIENT_ID = os.getenv("X_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("X_CLIENT_SECRET", "").strip()
BASE_URL = os.getenv("APP_BASE_URL", "https://socialpilot-ai-mvp.onrender.com").strip().rstrip("/")
REDIRECT_URI = os.getenv("X_REDIRECT_URI", BASE_URL + "/auth/x/callback").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
SCOPES = "tweet.read tweet.write users.read offline.access"

def db():
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured.")
    url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
    return psycopg.connect(url, connect_timeout=10)

def workspace_for(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE, "")
    session = _read_session(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="Log in at /account before connecting X.")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT w.id FROM customer_workspaces w JOIN customer_accounts a ON a.id=w.owner_account_id WHERE a.id=%s AND a.is_active=TRUE", (session["sub"],))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Customer workspace not found or disabled.")
    return str(row[0])

def ensure_tables(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS x_oauth_states (state_hash TEXT PRIMARY KEY, workspace_id UUID NOT NULL, code_verifier TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
    cur.execute("CREATE TABLE IF NOT EXISTS social_connections (id BIGSERIAL PRIMARY KEY, workspace_id UUID NOT NULL, platform TEXT NOT NULL, provider_user_id TEXT NOT NULL, display_name TEXT, encrypted_access_token TEXT NOT NULL, expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(workspace_id, platform, provider_user_id))")
    cur.execute("ALTER TABLE social_connections ADD COLUMN IF NOT EXISTS encrypted_refresh_token TEXT")

def encrypt(value: str) -> str:
    if not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured.")
    return Fernet(ENCRYPTION_KEY.encode("ascii")).encrypt(value.encode()).decode("ascii")

def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

@router.get("/auth/x/start")
async def x_start(request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Set X_CLIENT_ID and X_CLIENT_SECRET in Render Environment.")
    workspace_id = workspace_for(request)
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM x_oauth_states WHERE created_at < NOW() - INTERVAL '15 minutes'")
            cur.execute("INSERT INTO x_oauth_states(state_hash,workspace_id,code_verifier) VALUES (%s,%s,%s)", (hashlib.sha256(state.encode()).hexdigest(), workspace_id, verifier))
        conn.commit()
    params = {"response_type":"code","client_id":CLIENT_ID,"redirect_uri":REDIRECT_URI,"scope":SCOPES,"state":state,"code_challenge":pkce_challenge(verifier),"code_challenge_method":"S256"}
    return RedirectResponse("https://twitter.com/i/oauth2/authorize?" + urlencode(params), status_code=302)

@router.get("/auth/x/callback")
async def x_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"connected":False,"platform":"x","error":"X authorization was denied or cancelled."})
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing X OAuth code/state.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM x_oauth_states WHERE state_hash=%s AND created_at >= NOW() - INTERVAL '15 minutes' RETURNING workspace_id,code_verifier", (hashlib.sha256(state.encode()).hexdigest(),))
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=400, detail="X OAuth state is invalid, expired, or already used.")
    if not CLIENT_ID or not CLIENT_SECRET or not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="X credentials or TOKEN_ENCRYPTION_KEY are not configured.")
    workspace_id, verifier = str(row[0]), row[1]
    async with httpx.AsyncClient(timeout=25) as client:
        token_response = await client.post("https://api.x.com/2/oauth2/token", data={"grant_type":"authorization_code","code":code,"redirect_uri":REDIRECT_URI,"code_verifier":verifier}, auth=(CLIENT_ID,CLIENT_SECRET), headers={"Content-Type":"application/x-www-form-urlencoded"})
        if token_response.is_error:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"x","step":"token_exchange","http_status":token_response.status_code,"error":"X token exchange failed; verify callback URL, client type and OAuth 2.0 settings."})
        token_data = token_response.json()
        access = token_data.get("access_token")
        if not access:
            raise HTTPException(status_code=502, detail="X did not return an access token.")
        me_response = await client.get("https://api.x.com/2/users/me", params={"user.fields":"name,username"}, headers={"Authorization":"Bearer "+access})
        if me_response.is_error:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"x","step":"profile_lookup","http_status":me_response.status_code,"error":"X account lookup failed; check users.read permission."})
        user = (me_response.json().get("data") or {})
    user_id = str(user.get("id") or "")
    username = str(user.get("username") or "")
    if not user_id:
        raise HTTPException(status_code=502, detail="X account ID was not returned.")
    refresh = token_data.get("refresh_token")
    expires_in = int(token_data.get("expires_in") or 0)
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("""INSERT INTO social_connections(workspace_id,platform,provider_user_id,display_name,encrypted_access_token,encrypted_refresh_token,expires_at)
                VALUES (%s,'x',%s,%s,%s,%s,CASE WHEN %s > 0 THEN NOW() + (%s * INTERVAL '1 second') ELSE NULL END)
                ON CONFLICT(workspace_id,platform,provider_user_id) DO UPDATE SET display_name=EXCLUDED.display_name,encrypted_access_token=EXCLUDED.encrypted_access_token,encrypted_refresh_token=COALESCE(EXCLUDED.encrypted_refresh_token,social_connections.encrypted_refresh_token),expires_at=EXCLUDED.expires_at,updated_at=NOW()""",
                (workspace_id,user_id,username or str(user.get("name") or "X account"),encrypt(access),encrypt(refresh) if refresh else None,expires_in,expires_in))
        conn.commit()
    return RedirectResponse(BASE_URL + "/platforms?x=connected", status_code=303)

class XPostInput(BaseModel):
    text: str = Field(min_length=1, max_length=280)

@router.post("/api/x/posts")
async def publish_x_post(payload: XPostInput, request: Request):
    workspace_id = workspace_for(request)
    if not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("SELECT provider_user_id,encrypted_access_token,encrypted_refresh_token,expires_at FROM social_connections WHERE workspace_id=%s AND platform='x' ORDER BY updated_at DESC LIMIT 1", (workspace_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=409, detail="Connect X first at /auth/x/start.")
    provider_user_id = row[0]
    access = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[1].encode("ascii")).decode()
    refresh = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[2].encode("ascii")).decode() if row[2] else None
    if row[3] and row[3].timestamp() <= time.time():
        if not refresh:
            raise HTTPException(status_code=409, detail="X access token expired; reconnect X.")
        async with httpx.AsyncClient(timeout=25) as client:
            tr = await client.post("https://api.x.com/2/oauth2/token", data={"grant_type":"refresh_token","refresh_token":refresh}, auth=(CLIENT_ID,CLIENT_SECRET), headers={"Content-Type":"application/x-www-form-urlencoded"})
            if tr.is_error:
                raise HTTPException(status_code=502, detail="X token refresh failed; reconnect X.")
            td = tr.json()
        access = td["access_token"]
        new_refresh = td.get("refresh_token", refresh)
        exp = int(td.get("expires_in") or 0)
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE social_connections SET encrypted_access_token=%s,encrypted_refresh_token=%s,expires_at=CASE WHEN %s>0 THEN NOW()+(%s*INTERVAL '1 second') ELSE NULL END,updated_at=NOW() WHERE workspace_id=%s AND platform='x' AND provider_user_id=%s", (encrypt(access),encrypt(new_refresh),exp,exp,workspace_id,provider_user_id))
            conn.commit()
    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.post("https://api.x.com/2/tweets", json={"text":payload.text}, headers={"Authorization":"Bearer "+access,"Content-Type":"application/json"})
    if resp.is_error:
        raise HTTPException(status_code=502, detail={"message":"X rejected the post. Check API plan, permissions and rate limits.","provider_status":resp.status_code})
    data = resp.json().get("data") or {}
    return {"published":True,"platform":"x","post_id":data.get("id"),"text":payload.text}
