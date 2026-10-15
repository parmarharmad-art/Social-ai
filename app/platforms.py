"""Honest multi-platform connection hub for SocialPilot AI."""
import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PLATFORMS = [
    {"id":"instagram","name":"Instagram","group":"Meta","status":"blocked","note":"Kept pending as requested: Meta is returning API access blocked; no Instagram connect action is offered."},
    {"id":"facebook","name":"Facebook Pages","group":"Meta","status":"oauth_implemented","note":"Facebook Login fallback exists; requires matching Meta credentials and a Page-linked professional Instagram account where applicable."},
    {"id":"linkedin","name":"LinkedIn Profiles","group":"Professional","status":"oauth_implemented","note":"OAuth and text-post publishing endpoints added. Requires LinkedIn app credentials, OpenID Connect and w_member_social approval."},
    {"id":"youtube","name":"YouTube","group":"Video","status":"oauth_implemented","note":"Google OAuth and channel verification code added. Requires Google OAuth credentials, YouTube Data API v3 and consent-screen approval; video upload is not yet implemented."},
    {"id":"tiktok","name":"TikTok","group":"Video","status":"planned","note":"Requires TikTok developer app approval and Content Posting API access."},
    {"id":"pinterest","name":"Pinterest","group":"Discovery","status":"oauth_implemented","note":"OAuth and image-pin publishing code added. Requires Pinterest app access, user_accounts:read and pins:write permissions, plus a board ID and public HTTPS image."},
    {"id":"x","name":"X","group":"Conversation","status":"oauth_implemented","note":"OAuth 2.0 PKCE and text-post publishing code added. Requires X developer app, OAuth 2.0 user authentication and API access."},
]

@router.get("/api/platforms")
async def platform_catalog():
    return {
        "product": "SocialPilot AI",
        "mode": "multi-platform",
        "platforms": [
            {**p, "connect_url": (
                None if p["id"] == "instagram" else
                "/auth/facebook/start" if p["id"] == "facebook" else
                "/auth/linkedin/start" if p["id"] == "linkedin" else
                "/auth/youtube/start" if p["id"] == "youtube" else
                "/auth/x/start" if p["id"] == "x" else
                "/auth/pinterest/start" if p["id"] == "pinterest" else None
            )} for p in PLATFORMS
        ],
        "notice": "A listed OAuth flow is not proof of successful connection or publishing. Provider approval and live tests are required."
    }


@router.get("/api/integration-readiness")
async def integration_readiness():
    """Safe configuration checklist; never returns secret values."""
    def configured(name):
        return bool(os.getenv(name, "").strip())
    return {
        "signup_enabled": os.getenv("CUSTOMER_SIGNUP_ENABLED", "false").strip().lower() == "true",
        "openai_api_key": configured("OPENAI_API_KEY"),
        "automation_api_key": configured("AUTOMATION_API_KEY"),
        "mcp_access_token": configured("MCP_ACCESS_TOKEN") or configured("AUTOMATION_API_KEY"),
        "facebook_credentials": configured("META_APP_ID") and configured("META_APP_SECRET"),
        "linkedin_credentials": configured("LINKEDIN_CLIENT_ID") and configured("LINKEDIN_CLIENT_SECRET"),
        "youtube_credentials": configured("GOOGLE_CLIENT_ID") and configured("GOOGLE_CLIENT_SECRET"),
        "x_credentials": configured("X_CLIENT_ID") and configured("X_CLIENT_SECRET"),
        "pinterest_credentials": configured("PINTEREST_APP_ID") and configured("PINTEREST_APP_SECRET"),
        "database_configured": configured("DATABASE_URL"),
        "token_encryption_key": configured("TOKEN_ENCRYPTION_KEY"),
        "customer_session_secret": len(os.getenv("CUSTOMER_SESSION_SECRET", os.getenv("SESSION_SECRET", "")).strip()) >= 32,
        "instagram": "pending_by_user_request",
        "razorpay": "pending_by_user_request",
        "note": "Credentials being present does not prove provider approval or a successful live publish."
    }

@router.get("/platforms", response_class=HTMLResponse)
async def platforms_page():
    cards = []
    for p in PLATFORMS:
        ready = p["status"] == "oauth_implemented"
        label = "OAuth flow in code — test required" if ready else ("Blocked / pending" if p["id"] == "instagram" else "Integration planned")
        action = (
            f'<a class="btn" href="{"/auth/linkedin/start" if p["id"]=="linkedin" else "/auth/youtube/start" if p["id"]=="youtube" else "/auth/x/start" if p["id"]=="x" else "/auth/pinterest/start" if p["id"]=="pinterest" else "/auth/facebook/start"}">Try connect</a>'
            if ready and p["id"] != "instagram" else ('<span class="btn disabled">Pending by request</span>' if p["id"] == "instagram" else '<span class="btn disabled">Coming soon</span>')
        )
        cards.append(
            f'<article><div class="top"><span class="group">{p["group"]}</span><span class="status {"code" if ready else "planned"}">{label}</span></div>'
            f'<h2>{p["name"]}</h2><p>{p["note"]}</p>{action}</article>'
        )
    return HTMLResponse("""<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SocialPilot AI · Platforms</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#f4f7ff;font:16px system-ui,sans-serif}
main{max-width:1050px;margin:auto;padding:28px 18px 48px}.eyebrow{color:#8be9ff;font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:12px}
h1{font-size:clamp(30px,6vw,46px);line-height:1.08;margin:12px 0} .sub{color:#bac5dd;max-width:720px;line-height:1.6}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:14px;margin-top:26px}
article{border:1px solid #293450;background:#121a2e;border-radius:16px;padding:18px;display:flex;flex-direction:column;min-height:225px}
.top{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap}.group{font-size:12px;color:#b9c8e7}
.status{font-size:11px;border-radius:999px;padding:5px 8px}.code{background:#203b4a;color:#9cecff}.planned{background:#303246;color:#d6d7e7}
h2{font-size:20px;margin:18px 0 8px}p{color:#bac5dd;line-height:1.5;font-size:14px;flex:1}
.btn{display:inline-block;text-align:center;padding:10px 13px;border-radius:9px;background:#b8f2ff;color:#07121d;font-weight:700;text-decoration:none;width:max-content;max-width:100%}
.disabled{background:#282f43;color:#b8c0d5}.notice{margin-top:22px;border-left:3px solid #8be9ff;padding:12px 14px;background:#121a2e;color:#c5d0e5;line-height:1.5;font-size:13px}
nav{display:flex;gap:16px;margin-top:22px;flex-wrap:wrap}nav a{color:#8be9ff}
</style><main><div class="eyebrow">SocialPilot AI · Connect channels</div><h1>All your social platforms.<br>One workspace.</h1><p class="sub">Plan content for multiple channels from one place. Connections are being added provider by provider. We show the current integration state honestly—no fake connected badges.</p>
<div class="grid">""" + "".join(cards) + """</div>
<div class="notice"><strong>Important:</strong> “OAuth flow in code” does not mean the provider has approved the app or that publishing works. Meta currently blocks the Instagram token exchange. LinkedIn OAuth/text-post and YouTube OAuth/channel verification code are available but need provider credentials and approval. YouTube video upload and TikTok publishing are not yet implemented. Pinterest image-pin publishing is implemented in code but requires app access and live testing. X text posting is implemented in code but requires credentials and a live-account test.</div>
<nav><a href="/dashboard">Dashboard</a><a href="/workspace">Workspace</a><a href="/account">Account / Login</a><a href="/setup">Setup checklist</a></nav></main></html>""")
