"""LinkedIn OAuth and text publishing endpoints for SocialPilot AI."""
import hashlib
import os
import time
from urllib.parse import urlencode

import httpx
import psycopg
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
from app.customer_auth import SESSION_COOKIE, _read_session

router = APIRouter(tags=["linkedin"])
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
BASE_URL = os.getenv("APP_BASE_URL", "https://socialpilot-ai-mvp.onrender.com").strip().rstrip("/")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", BASE_URL + "/auth/linkedin/callback").strip()
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
        raise HTTPException(status_code=401, detail="Log in at /account before connecting LinkedIn.")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT w.id FROM customer_workspaces w JOIN customer_accounts a ON a.id=w.owner_account_id WHERE a.id=%s AND a.is_active=TRUE", (session["sub"],))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Customer workspace not found or disabled.")
    return str(row[0])

def ensure_tables(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS linkedin_oauth_states (state_hash TEXT PRIMARY KEY, workspace_id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
    cur.execute("CREATE TABLE IF NOT EXISTS social_connections (id BIGSERIAL PRIMARY KEY, workspace_id UUID NOT NULL, platform TEXT NOT NULL, provider_user_id TEXT NOT NULL, display_name TEXT, encrypted_access_token TEXT NOT NULL, expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(workspace_id, platform, provider_user_id))")
    cur.execute("CREATE TABLE IF NOT EXISTS social_publish_log (id BIGSERIAL PRIMARY KEY, workspace_id UUID NOT NULL, platform TEXT NOT NULL, provider_post_id TEXT, text_content TEXT NOT NULL, status TEXT NOT NULL, error TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")

@router.get("/auth/linkedin/start")
async def linkedin_start(request: Request):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in Render Environment.")
    workspace_id = workspace_for(request)
    state = __import__("secrets").token_urlsafe(32)
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM linkedin_oauth_states WHERE created_at < NOW() - INTERVAL '15 minutes'")
            cur.execute("INSERT INTO linkedin_oauth_states(state_hash, workspace_id) VALUES (%s,%s)", (hashlib.sha256(state.encode()).hexdigest(), workspace_id))
        conn.commit()
    params = {"response_type":"code", "client_id":CLIENT_ID, "redirect_uri":REDIRECT_URI, "state":state, "scope":"openid profile w_member_social"}
    return RedirectResponse("https://www.linkedin.com/oauth/v2/authorization?" + urlencode(params), status_code=302)

@router.get("/auth/linkedin/callback")
async def linkedin_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"connected":False,"platform":"linkedin","error":"LinkedIn authorization was denied or cancelled."})
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing LinkedIn OAuth code/state.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("DELETE FROM linkedin_oauth_states WHERE state_hash=%s AND created_at >= NOW() - INTERVAL '15 minutes' RETURNING workspace_id", (hashlib.sha256(state.encode()).hexdigest(),))
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=400, detail="LinkedIn OAuth state is invalid, expired, or already used.")
    if not CLIENT_ID or not CLIENT_SECRET or not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="LinkedIn credentials or TOKEN_ENCRYPTION_KEY are not configured.")
    async with httpx.AsyncClient(timeout=25) as client:
        token_response = await client.post("https://www.linkedin.com/oauth/v2/accessToken", data={"grant_type":"authorization_code","code":code,"redirect_uri":REDIRECT_URI,"client_id":CLIENT_ID,"client_secret":CLIENT_SECRET}, headers={"Content-Type":"application/x-www-form-urlencoded"})
        if token_response.is_error:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"linkedin","step":"token_exchange","http_status":token_response.status_code,"error":"LinkedIn token exchange failed. Check redirect URI, credentials and app approval."})
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="LinkedIn did not return an access token.")
        profile_response = await client.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization":"Bearer " + access_token})
        if profile_response.is_error:
            return JSONResponse(status_code=502, content={"connected":False,"platform":"linkedin","step":"profile","http_status":profile_response.status_code,"error":"LinkedIn userinfo failed. Enable OpenID Connect and profile scope in the developer app."})
        profile = profile_response.json()
    provider_id = str(profile.get("sub") or "").strip()
    if not provider_id:
        raise HTTPException(status_code=502, detail="LinkedIn profile ID missing from userinfo.")
    encrypted = Fernet(ENCRYPTION_KEY.encode("ascii")).encrypt(access_token.encode()).decode("ascii")
    expires_in = int(token_data.get("expires_in") or 0)
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("""INSERT INTO social_connections(workspace_id,platform,provider_user_id,display_name,encrypted_access_token,expires_at)
            VALUES (%s,'linkedin',%s,%s,%s,CASE WHEN %s > 0 THEN NOW() + (%s * INTERVAL '1 second') ELSE NULL END)
            ON CONFLICT(workspace_id,platform,provider_user_id) DO UPDATE SET display_name=EXCLUDED.display_name,encrypted_access_token=EXCLUDED.encrypted_access_token,expires_at=EXCLUDED.expires_at,updated_at=NOW()""",
            (str(row[0]),provider_id,str(profile.get("name") or profile.get("given_name") or "LinkedIn member"),encrypted,expires_in,expires_in))
        conn.commit()
    return RedirectResponse(BASE_URL + "/platforms?linkedin=connected", status_code=303)

class LinkedInTextPost(BaseModel):
    text: str = Field(min_length=1, max_length=3000)

@router.post("/api/linkedin/posts")
async def linkedin_publish_text(payload: LinkedInTextPost, request: Request):
    workspace_id = workspace_for(request)
    if not ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured.")
    with db() as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)
            cur.execute("SELECT provider_user_id,encrypted_access_token,expires_at FROM social_connections WHERE workspace_id=%s AND platform='linkedin' ORDER BY updated_at DESC LIMIT 1", (workspace_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=409, detail="Connect LinkedIn first at /auth/linkedin/start.")
    if row[2] and row[2].timestamp() <= time.time():
        raise HTTPException(status_code=409, detail="LinkedIn token expired. Reconnect LinkedIn.")
    access_token = Fernet(ENCRYPTION_KEY.encode("ascii")).decrypt(row[1].encode("ascii")).decode()
    body = {"author":"urn:li:person:" + row[0],"commentary":payload.text,"visibility":"PUBLIC","distribution":{"feedDistribution":"MAIN_FEED","targetEntities":[]},"lifecycleState":"PUBLISHED","isReshareDisabled":False}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post("https://api.linkedin.com/rest/posts", json=body, headers={"Authorization":"Bearer " + access_token,"Content-Type":"application/json","LinkedIn-Version":os.getenv("LINKEDIN_API_VERSION","202601"),"X-Restli-Protocol-Version":"2.0.0"})
    if response.is_error:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO social_publish_log(workspace_id,platform,text_content,status,error) VALUES (%s,'linkedin',%s,'failed',%s)", (workspace_id,payload.text,(response.text or "LinkedIn publish failed")[:1000]))
            conn.commit()
        return JSONResponse(status_code=502, content={"published":False,"platform":"linkedin","http_status":response.status_code,"error":"LinkedIn rejected the post. Confirm w_member_social and Posts API access."})
    post_id = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO social_publish_log(workspace_id,platform,provider_post_id,text_content,status) VALUES (%s,'linkedin',%s,%s,'published')", (workspace_id,post_id,payload.text))
        conn.commit()
    return {"published":True,"platform":"linkedin","post_id":post_id}
