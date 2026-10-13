"""Authenticated Streamable HTTP MCP server for SocialPilot AI.

The MCP tools reuse the existing API logic. Requests to /mcp require a Bearer token:
MCP_ACCESS_TOKEN, falling back to AUTOMATION_API_KEY for easier first-time setup.
"""
import hmac
import os
from contextlib import AsyncExitStack
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app import main as api

mcp = FastMCP(
    "SocialPilot AI",
    instructions=(
        "Tools for Kiran Kumar's Instagram AI automation workspace. "
        "Check status before running actions. AI content/image generation may incur API charges. "
        "Scheduling tools create real Instagram post jobs; do not call them unless the user asks."
    ),
    streamable_http_path="/",
)


@mcp.tool()
async def get_automation_status() -> dict[str, Any]:
    """Check which SocialPilot AI services are configured. Does not expose secret values."""
    return await api.automation_status()


@mcp.tool()
async def get_content_topic_ideas() -> dict[str, Any]:
    """List practical AI automation topics for Kiran Kumar's Instagram account."""
    return await api.content_ideas()


@mcp.tool()
async def generate_instagram_content(topic: str) -> dict[str, Any]:
    """Generate an Instagram carousel outline, caption, CTA, hashtags and image prompt using the configured AI API. API usage may cost money."""
    return await api.generate_content({"topic": topic}, api.AUTOMATION_API_KEY)


@mcp.tool()
async def generate_instagram_image(prompt: str) -> dict[str, Any]:
    """Generate and host an Instagram image, returning a public HTTPS image URL. AI image API usage may cost money."""
    return await api.generate_image({"prompt": prompt}, api.AUTOMATION_API_KEY)


@mcp.tool()
async def list_scheduled_posts() -> dict[str, Any]:
    """List recent scheduled Instagram posts and their statuses."""
    return await api.list_posts(api.AUTOMATION_API_KEY)


@mcp.tool()
async def schedule_instagram_post(
    instagram_user_id: str,
    image_url: str,
    scheduled_at: str,
    caption: str,
    topic: str = "",
) -> dict[str, Any]:
    """Schedule one real Instagram image post. Requires a public HTTPS image URL and an ISO-8601 time with timezone, e.g. 2026-10-14T10:00:00+05:30. Only call when the user explicitly requests scheduling."""
    return await api.schedule_post(
        {
            "instagram_user_id": instagram_user_id,
            "image_url": image_url,
            "scheduled_at": scheduled_at,
            "caption": caption,
            "topic": topic,
        },
        api.AUTOMATION_API_KEY,
    )


@mcp.tool()
async def queue_two_instagram_posts(
    instagram_user_id: str = "",
    target_date: str = "",
) -> dict[str, Any]:
    """Generate and queue two Instagram posts for a future date at 10:00 and 18:00 India time. This invokes AI text and image generation and may incur API charges. Only call when the user explicitly asks to create/queue the posts."""
    payload: dict[str, str] = {}
    if instagram_user_id.strip():
        payload["instagram_user_id"] = instagram_user_id.strip()
    if target_date.strip():
        payload["target_date"] = target_date.strip()
    return await api.queue_daily_endpoint(payload, api.AUTOMATION_API_KEY)


@mcp.tool()
async def get_instagram_report(instagram_user_id: str = "") -> dict[str, Any]:
    """Fetch recent Instagram post likes/comments and basic recommendations. Requires a saved Instagram token."""
    user_id = instagram_user_id.strip() or api.INSTAGRAM_USER_ID
    if not user_id:
        raise ValueError("Instagram user ID is not configured. Supply instagram_user_id.")
    return await api.instagram_report(user_id, api.AUTOMATION_API_KEY)


def mount_mcp(application: FastAPI) -> None:
    """Protect and mount the remote MCP endpoint at /mcp/."""
    mcp_http_app = mcp.streamable_http_app(
        transport_security=TransportSecuritySettings(
            allowed_hosts=["socialpilot-ai-mvp.onrender.com", "socialpilot-ai-mvp.onrender.com:*"],
            allowed_origins=["https://socialpilot-ai-mvp.onrender.com"],
        ),
    )
    session_stack = AsyncExitStack()

    @application.on_event("startup")
    async def start_mcp_session_manager():
        await session_stack.__aenter__()
        await session_stack.enter_async_context(mcp.session_manager.run())

    @application.on_event("shutdown")
    async def stop_mcp_session_manager():
        await session_stack.aclose()

    @application.middleware("http")
    async def require_mcp_bearer(request: Request, call_next):
        if request.url.path == "/mcp" or request.url.path.startswith("/mcp/"):
            expected = (os.getenv("MCP_ACCESS_TOKEN") or api.AUTOMATION_API_KEY).strip()
            if not expected:
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Configure MCP_ACCESS_TOKEN or AUTOMATION_API_KEY on the server."},
                )
            authorization = request.headers.get("authorization", "")
            provided = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
            if not provided or not hmac.compare_digest(provided, expected):
                return JSONResponse(status_code=401, content={"detail": "A valid Bearer token is required for the MCP endpoint."})
        return await call_next(request)

    application.mount("/mcp", mcp_http_app)
