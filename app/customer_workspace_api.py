"""Session-authenticated, workspace-scoped customer APIs.

These routes deliberately do not accept the global automation API key. All customer
queries are scoped to the workspace resolved from the signed customer session.
"""
import os
from datetime import datetime, timezone
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.customer_auth import SESSION_COOKIE, _read_session

router = APIRouter(prefix="/api/customer", tags=["customer-workspace"])


def _db():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return psycopg.connect(url, connect_timeout=10)


def _workspace_id(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE, "")
    session = _read_session(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="Log in at /account first.")
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT w.id
                FROM customer_workspaces w
                JOIN customer_accounts a ON a.id=w.owner_account_id
                WHERE a.id=%s AND a.is_active=TRUE
            """, (session["sub"],))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Customer workspace is unavailable.")
    return str(row[0])


def _ensure_posts_table(cur):
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
            published_at TIMESTAMPTZ,
            workspace_id UUID
        )
    """)
    cur.execute("ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS workspace_id UUID")


class CustomerScheduleInput(BaseModel):
    instagram_user_id: str = Field(min_length=1, max_length=128)
    image_url: str = Field(min_length=9, max_length=2048)
    caption: str = Field(min_length=1, max_length=2200)
    scheduled_at: datetime
    topic: str = Field(default="", max_length=300)


@router.get("/instagram/connections")
async def customer_connections(request: Request):
    workspace_id = _workspace_id(request)
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS instagram_connections (
                    instagram_user_id TEXT PRIMARY KEY,
                    encrypted_access_token TEXT NOT NULL,
                    token_expires_in BIGINT,
                    auth_method TEXT NOT NULL DEFAULT 'instagram_login',
                    workspace_id UUID,
                    connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE instagram_connections ADD COLUMN IF NOT EXISTS workspace_id UUID")
            cur.execute("ALTER TABLE instagram_connections ADD COLUMN IF NOT EXISTS auth_method TEXT NOT NULL DEFAULT 'instagram_login'")
            cur.execute("""
                SELECT instagram_user_id, auth_method, connected_at, updated_at
                FROM instagram_connections
                WHERE workspace_id=%s
                ORDER BY connected_at DESC
            """, (workspace_id,))
            rows = cur.fetchall()
    return {"connections": [
        {"instagram_user_id": row[0], "auth_method": row[1],
         "connected_at": row[2].isoformat() if row[2] else None,
         "updated_at": row[3].isoformat() if row[3] else None}
        for row in rows
    ]}


@router.get("/posts")
async def customer_posts(request: Request):
    workspace_id = _workspace_id(request)
    with _db() as conn:
        with conn.cursor() as cur:
            _ensure_posts_table(cur)
            cur.execute("""
                SELECT id, instagram_user_id, caption, scheduled_at, status,
                       instagram_media_id, last_error
                FROM scheduled_posts
                WHERE workspace_id=%s
                ORDER BY scheduled_at DESC LIMIT 100
            """, (workspace_id,))
            rows = cur.fetchall()
        conn.commit()
    return {"posts": [
        {"id": row[0], "instagram_user_id": row[1], "caption": row[2],
         "scheduled_at": row[3].isoformat(), "status": row[4],
         "instagram_media_id": row[5], "last_error": row[6]}
        for row in rows
    ]}


@router.post("/posts")
async def customer_schedule_post(payload: CustomerScheduleInput, request: Request):
    workspace_id = _workspace_id(request)
    if not payload.image_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="image_url must be a public HTTPS URL.")
    when = payload.scheduled_at
    if when.tzinfo is None:
        raise HTTPException(status_code=400, detail="scheduled_at must include a timezone.")
    when = when.astimezone(timezone.utc)
    if when <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Choose a future publish time.")
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM instagram_connections
                WHERE instagram_user_id=%s AND workspace_id=%s
            """, (payload.instagram_user_id, workspace_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Instagram account is not connected to this workspace.")
            _ensure_posts_table(cur)
            cur.execute("""
                INSERT INTO scheduled_posts
                    (instagram_user_id, image_url, caption, scheduled_at, workspace_id)
                VALUES (%s,%s,%s,%s,%s)
                RETURNING id,status,scheduled_at
            """, (payload.instagram_user_id, payload.image_url, payload.caption, when, workspace_id))
            row = cur.fetchone()
        conn.commit()
    return {"ok": True, "post_id": row[0], "status": row[1],
            "scheduled_at": row[2].isoformat(), "workspace_id": workspace_id}


@router.get("/workspace", include_in_schema=False)
async def customer_workspace_page():
    """Simple session-authenticated customer console for account linking and post scheduling."""
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""<!doctype html>
<html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SocialPilot AI Workspace</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#eef3ff;font:16px/1.5 system-ui}
main{max-width:900px;margin:auto;padding:20px}.top,.panel{background:#151d32;border:1px solid #2b3855;border-radius:16px;padding:18px;margin:14px 0}
h1,h2{margin-top:0}p,small{color:#b8c5df}a{color:#8fb5ff}input,textarea,button,select{font:inherit;width:100%;padding:12px;margin:6px 0;border-radius:9px;border:1px solid #3d4b69;background:#0b1020;color:#eef3ff}
button{background:#4779ed;border:0;font-weight:700;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}.item{padding:12px;border:1px solid #33415d;border-radius:10px;margin:8px 0;overflow-wrap:anywhere}.status{white-space:pre-wrap;color:#bfe6c9}.warn{background:#2a2436;border-radius:10px;padding:12px;color:#ffe4b5}
</style></head><body><main>
<section class="top"><h1>SocialPilot AI</h1><p>Your workspace for Instagram connections and scheduled posts.</p><p><a href="/account">Account & login</a> · <a href="/studio">Post & Video Studio</a> · <a href="/setup">Setup status</a> · <a href="/sell">Product overview</a></p><div class="warn">Early access: connect your Instagram account first. Scheduling requires a public HTTPS image URL. Confirm a test post before relying on automated publishing.</div><p id="message" class="status">Checking your session…</p><button id="refresh" type="button">Refresh workspace</button><button id="logout" type="button">Log out</button></section>
<div class="grid"><section class="panel"><h2>1. Connect Instagram</h2><p>Sign in with the Instagram account you want this workspace to manage.</p><a href="/auth/instagram/start"><button type="button">Connect Instagram</button></a><div id="connections"></div></section>
<section class="panel"><h2>2. Schedule an image post</h2><form id="schedule"><label>Instagram account</label><select id="account" required><option value="">Connect an account first</option></select><label>Public HTTPS image URL</label><input id="image" type="url" placeholder="https://example.com/post.jpg" required><label>Caption</label><textarea id="caption" rows="5" maxlength="2200" required placeholder="Write your caption…"></textarea><label>Publish date & time (your phone's local time)</label><input id="when" type="datetime-local" required><button type="submit">Schedule post</button></form><small>Use an image URL that Instagram can access without logging in. Studio export is not automatically uploaded to a hosted media library yet.</small></section></div>
<section class="panel"><h2>Scheduled & recent posts</h2><div id="posts"><p>Loading…</p></div></section>
</main><script>
const $=id=>document.getElementById(id);const msg=$('message');
async function request(url,opts={}){const r=await fetch(url,{credentials:'same-origin',...opts});let d={};try{d=await r.json()}catch{}if(!r.ok)throw new Error(d.detail||d.error||('Request failed ('+r.status+')'));return d}
function localIso(v){const d=new Date(v);const off=-d.getTimezoneOffset();const sign=off>=0?'+':'-';const z=n=>String(Math.floor(Math.abs(n))).padStart(2,'0');return d.getFullYear()+'-'+z(d.getMonth()+1)+'-'+z(d.getDate())+'T'+z(d.getHours())+':'+z(d.getMinutes())+':00'+sign+z(off/60)+':'+z(off%60)}
async function refresh(){try{const me=await request('/api/account/me');msg.textContent='Signed in as '+me.account.email+' · Workspace: '+me.workspace.name;const c=await request('/api/customer/instagram/connections');$('connections').innerHTML=c.connections.length?c.connections.map(x=>'<div class="item"><b>Instagram ID:</b> '+x.instagram_user_id+'<br><small>Connected via '+x.auth_method+'</small></div>').join(''):'<p>No Instagram account connected yet.</p>';const sel=$('account');sel.innerHTML='<option value="">Select Instagram account</option>'+c.connections.map(x=>'<option value="'+x.instagram_user_id+'">'+x.instagram_user_id+'</option>').join('');const p=await request('/api/customer/posts');$('posts').innerHTML=p.posts.length?p.posts.map(x=>'<div class="item"><b>'+x.status+'</b> · '+new Date(x.scheduled_at).toLocaleString()+'<p>'+escapeHtml(x.caption)+'</p>'+(x.last_error?'<small>Error: '+escapeHtml(x.last_error)+'</small>':'')+(x.instagram_media_id?'<small> Published media ID: '+x.instagram_media_id+'</small>':'')+'</div>').join(''):'<p>No scheduled posts yet.</p>'}catch(e){msg.textContent=e.message;if(e.message.includes('Log in')||e.message.includes('Please log in'))msg.innerHTML=escapeHtml(e.message)+' · <a href="/account">Open account login</a>'}}
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
$('refresh').onclick=refresh;$('schedule').onsubmit=async e=>{e.preventDefault();try{const d=await request('/api/customer/posts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({instagram_user_id:$('account').value,image_url:$('image').value,caption:$('caption').value,scheduled_at:localIso($('when').value)})});msg.textContent='Post scheduled. Queue ID: '+d.post_id;$('caption').value='';await refresh()}catch(err){msg.textContent=err.message}};
$('logout').onclick=async()=>{try{await request('/api/account/logout',{method:'POST'});location.href='/account'}catch(e){msg.textContent=e.message}};refresh();
</script></body></html>""")
