"""Customer account primitives for SocialPilot AI.

Signup is disabled by default until the operator sets CUSTOMER_SIGNUP_ENABLED=true
and CUSTOMER_SESSION_SECRET to a long random secret. This module intentionally does
not claim tenant isolation for legacy automation routes; customer-facing routes must
scope every database query to the authenticated workspace before public launch.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter()
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SESSION_COOKIE = "socialpilot_session"
SESSION_SECONDS = 60 * 60 * 24 * 7


def _db():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured.")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return psycopg.connect(url, connect_timeout=10)


def _session_secret() -> bytes:
    secret = os.getenv("CUSTOMER_SESSION_SECRET", "").strip()
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="Customer login is not configured securely. Set CUSTOMER_SESSION_SECRET to a random secret of at least 32 characters.")
    return secret.encode("utf-8")


def _ensure_tables():
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customer_accounts (
                    id UUID PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customer_workspaces (
                    id UUID PRIMARY KEY,
                    owner_account_id UUID NOT NULL UNIQUE REFERENCES customer_accounts(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        conn.commit()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return "pbkdf2_sha256$310000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _make_session(account_id: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": account_id, "exp": int(time.time()) + SESSION_SECONDS}, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_session_secret(), payload.encode(), hashlib.sha256).digest()
    return payload + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")


def _read_session(token: str) -> dict[str, Any] | None:
    try:
        payload, sig = token.split(".", 1)
        expected = hmac.new(_session_secret(), payload.encode(), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode((sig + "=" * (-len(sig) % 4)).encode())
        if not hmac.compare_digest(actual, expected):
            return None
        raw = base64.urlsafe_b64decode((payload + "=" * (-len(payload) % 4)).encode())
        data = json.loads(raw)
        if int(data.get("exp", 0)) < int(time.time()) or not data.get("sub"):
            return None
        return data
    except (ValueError, TypeError, json.JSONDecodeError, HTTPException):
        return None


def _set_cookie(response: Response, account_id: str):
    response.set_cookie(SESSION_COOKIE, _make_session(account_id), max_age=SESSION_SECONDS,
                        httponly=True, secure=True, samesite="lax", path="/")


def _signup_enabled() -> bool:
    return os.getenv("CUSTOMER_SIGNUP_ENABLED", "false").strip().lower() == "true"


class SignupInput(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    workspace_name: str = Field(default="My workspace", min_length=2, max_length=80)


class LoginInput(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=256)


@router.get("/account", response_class=HTMLResponse)
async def account_page():
    return HTMLResponse("""<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SocialPilot AI account</title>
<style>body{font:16px system-ui;background:#0b1020;color:#f4f7ff;margin:0;padding:24px}.wrap{max-width:460px;margin:5vh auto;background:#151d32;padding:24px;border-radius:18px}input,button{box-sizing:border-box;width:100%;padding:13px;margin:7px 0;border-radius:9px;border:1px solid #52607a}input{background:#0b1020;color:white}button{background:#5e8cff;color:white;font-weight:700;border:0}small{color:#b6c1d7}#msg{white-space:pre-wrap}</style>
<div class="wrap"><h1>SocialPilot AI</h1><p>Customer account access</p><form id="signup"><h2>Create account</h2><input name="email" type="email" placeholder="Email" required><input name="workspace_name" placeholder="Workspace name" value="My workspace" required><input name="password" type="password" minlength="12" placeholder="Password (12+ characters)" required><button>Create account</button></form><hr><form id="login"><h2>Log in</h2><input name="email" type="email" placeholder="Email" required><input name="password" type="password" placeholder="Password" required><button>Log in</button></form><button id="me" type="button">Check session</button><button id="logout" type="button">Log out</button><p id="msg"></p><small>Use a unique password. Account signup is enabled only after the operator configures secure session settings. Instagram publishing and paid plans are not activated by this page.</small></div>
<script>
const msg=document.getElementById('msg');
async function send(url,body){try{const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});const d=await r.json();msg.textContent=r.ok?JSON.stringify(d,null,2):(d.detail||'Request failed');}catch(e){msg.textContent='Request failed: '+e.message}}
document.getElementById('signup').onsubmit=e=>{e.preventDefault();const f=new FormData(e.target);send('/api/account/signup',{email:f.get('email'),password:f.get('password'),workspace_name:f.get('workspace_name')})};
document.getElementById('login').onsubmit=e=>{e.preventDefault();const f=new FormData(e.target);send('/api/account/login',{email:f.get('email'),password:f.get('password')})};
document.getElementById('me').onclick=async()=>{const r=await fetch('/api/account/me',{credentials:'same-origin'});msg.textContent=JSON.stringify(await r.json(),null,2)};
document.getElementById('logout').onclick=async()=>{const r=await fetch('/api/account/logout',{method:'POST',credentials:'same-origin'});msg.textContent=JSON.stringify(await r.json(),null,2)};
</script></html>""")


@router.post("/api/account/signup")
async def signup(payload: SignupInput, response: Response):
    if not _signup_enabled():
        raise HTTPException(status_code=503, detail="Customer signup is not enabled yet. The operator must finish production security setup first.")
    if not EMAIL_RE.fullmatch(payload.email.strip().lower()):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    _session_secret()
    _ensure_tables()
    account_id = __import__("uuid").uuid4()
    workspace_id = __import__("uuid").uuid4()
    email = payload.email.strip().lower()
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO customer_accounts (id,email,password_hash) VALUES (%s,%s,%s) RETURNING id", (account_id, email, _hash_password(payload.password)))
                cur.execute("INSERT INTO customer_workspaces (id,owner_account_id,name) VALUES (%s,%s,%s)", (workspace_id, account_id, payload.workspace_name.strip()))
            conn.commit()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    except Exception:
        raise HTTPException(status_code=503, detail="Could not create account. Please try again later.")
    _set_cookie(response, str(account_id))
    return {"ok": True, "account": {"id": str(account_id), "email": email}, "workspace": {"id": str(workspace_id), "name": payload.workspace_name.strip()}, "message": "Account created. Instagram features will be enabled after workspace isolation and publishing tests are complete."}


@router.post("/api/account/login")
async def login(payload: LoginInput, response: Response):
    _session_secret()
    _ensure_tables()
    email = payload.email.strip().lower()
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,password_hash,is_active FROM customer_accounts WHERE email=%s", (email,))
            row = cur.fetchone()
    if not row or not row[2] or not _verify_password(payload.password, row[1]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    _set_cookie(response, str(row[0]))
    return {"ok": True, "account": {"id": str(row[0]), "email": email}}


@router.get("/api/account/me")
async def me(request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    data = _read_session(token) if token else None
    if not data:
        raise HTTPException(status_code=401, detail="Please log in.")
    _ensure_tables()
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.id,a.email,w.id,w.name
                FROM customer_accounts a
                JOIN customer_workspaces w ON w.owner_account_id=a.id
                WHERE a.id=%s AND a.is_active=TRUE
            """, (data["sub"],))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Account not found or disabled.")
    return {"authenticated": True, "account": {"id": str(row[0]), "email": row[1]}, "workspace": {"id": str(row[2]), "name": row[3]}, "message": "Identity verified; workspace-bound Instagram APIs are still being implemented."}


@router.post("/api/account/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return {"ok": True, "message": "Logged out."}
