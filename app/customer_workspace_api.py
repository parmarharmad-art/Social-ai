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
