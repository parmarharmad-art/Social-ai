"""Session-authenticated, workspace-scoped customer APIs.

These routes deliberately do not accept the global automation API key. All customer
queries are scoped to the workspace resolved from the signed customer session.
"""
import os
import base64

import httpx
from datetime import datetime, timezone
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
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


class CustomerContentInput(BaseModel):
    topic: str = Field(min_length=3, max_length=300)




@router.post("/media/generate")
async def customer_generate_image(payload: CustomerContentInput, request: Request):
    workspace_id = _workspace_id(request)
    from uuid import uuid4
    from app.main import OPENAI_API_KEY, APP_BASE_URL, ensure_ai_tables
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="AI image generation is not configured yet.")
    topic = " ".join(payload.topic.split()).strip()
    prompt = (
        "Create a polished Instagram 4:5 social media infographic about " + topic +
        ". Use a clear headline, 3 to 5 concise workflow steps, readable large typography, "
        "dark navy background with white cards and electric blue/cyan accents, generous spacing, "
        "professional SaaS design, no fake logos, no tiny text. Footer: Kiran Kumar • AI Automation."
    )
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"model": os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
                      "prompt": prompt, "size": "1024x1024"},
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail="Image generation failed. Check AI provider access and quota.")
            raw = response.json()["data"][0].get("b64_json")
            if not raw:
                raise HTTPException(status_code=502, detail="Image provider returned no image data.")
            image_bytes = base64.b64decode(raw)
        ensure_ai_tables()
        asset_id = uuid4()
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE generated_assets ADD COLUMN IF NOT EXISTS workspace_id UUID")
                cur.execute("""
                    INSERT INTO generated_assets (asset_id, image_bytes, mime_type, workspace_id)
                    VALUES (%s,%s,%s,%s)
                """, (asset_id, image_bytes, "image/png", workspace_id))
            conn.commit()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Could not generate or store image. Check AI and database configuration.")
    return {"ok": True, "asset_id": str(asset_id),
            "image_url": f"{APP_BASE_URL}/assets/{asset_id}",
            "message": "Generated image saved to this workspace's media record."}


@router.post("/media/upload")
async def customer_upload_image(request: Request, file: UploadFile = File(...)):
    workspace_id = _workspace_id(request)
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG or WebP image.")
    data = await file.read(8 * 1024 * 1024 + 1)
    if not data or len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be smaller than 8 MB.")
    signatures = {
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }
    if not signatures.get(content_type, False):
        raise HTTPException(status_code=400, detail="The uploaded file does not match its image type.")
    from uuid import uuid4
    from app.main import APP_BASE_URL, ensure_ai_tables
    asset_id = uuid4()
    try:
        ensure_ai_tables()
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE generated_assets ADD COLUMN IF NOT EXISTS workspace_id UUID")
                cur.execute("""
                    INSERT INTO generated_assets (asset_id, image_bytes, mime_type, workspace_id)
                    VALUES (%s,%s,%s,%s)
                """, (asset_id, data, content_type, workspace_id))
            conn.commit()
    except Exception:
        raise HTTPException(status_code=503, detail="Could not store the image. Check database availability.")
    return {"ok": True, "asset_id": str(asset_id),
            "image_url": f"{APP_BASE_URL}/assets/{asset_id}",
            "message": "Image uploaded. You can use this public HTTPS URL for your scheduled post."}


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






@router.post("/content")
async def customer_generate_content(payload: CustomerContentInput, request: Request):
    # Require a valid session and workspace before spending any provider credits.
    _workspace_id(request)
    topic = " ".join(payload.topic.split()).strip()
    from app.main import OPENAI_API_KEY, make_template_content_package, openai_chat
    if not OPENAI_API_KEY:
        return {"ok": True, "mode": "template", "topic": topic,
                "content": make_template_content_package(topic),
                "note": "Template draft generated. AI writing requires the operator to configure the provider key."}
    generated = await openai_chat([
        {"role": "system", "content": "You are a practical Instagram content strategist for AI automation, digital marketing and small businesses. Write clear professional English, with concrete steps and no fabricated results."},
        {"role": "user", "content": "Create an Instagram carousel package with HOOK, SLIDE 1, SLIDE 2, SLIDE 3, SLIDE 4, CAPTION, CTA, HASHTAGS, IMAGE PROMPT sections. Keep each slide mobile-readable and practical. Topic: " + topic},
    ], max_tokens=1400)
    return {"ok": True, "mode": "ai", "topic": topic, "content": generated}



@router.delete("/posts/{post_id}")
async def customer_cancel_post(post_id: int, request: Request):
    workspace_id = _workspace_id(request)
    with _db() as conn:
        with conn.cursor() as cur:
            _ensure_posts_table(cur)
            cur.execute("""
                UPDATE scheduled_posts SET status='cancelled'
                WHERE id=%s AND workspace_id=%s AND status='scheduled'
                RETURNING id
            """, (post_id, workspace_id))
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled post not found in this workspace or it has already started.")
    return {"ok": True, "post_id": row[0], "status": "cancelled"}


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
