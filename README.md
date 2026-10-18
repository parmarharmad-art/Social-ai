# SocialPilot AI MVP

Mobile-first multi-platform social media management SaaS for **Kiran Kumar • AI Automation**.

- Repository: https://github.com/parmarharmad-art/Social-ai
- Render service: https://socialpilot-ai-mvp.onrender.com
- Dashboard (Metricool-style): https://socialpilot-ai-mvp.onrender.com/dashboard
- **Free AI Lip-Sync Studio:** https://socialpilot-ai-mvp.onrender.com/lipsync
- External open-source MuseTalk 1.5 ZeroGPU demo: https://huggingface.co/spaces/henrybit/musetalk-1-5
- Multi-platform connections: https://socialpilot-ai-mvp.onrender.com/platforms
- Platform catalog API: https://socialpilot-ai-mvp.onrender.com/api/platforms
- Planner: https://socialpilot-ai-mvp.onrender.com/planner
- Customer workspace: https://socialpilot-ai-mvp.onrender.com/workspace
- Customer account/login: https://socialpilot-ai-mvp.onrender.com/account

## Important: OAuth credential separation

Instagram connection is intentionally disabled/pending by product-owner request. For Facebook Page Login and Page publishing, configure `META_APP_ID` and `META_APP_SECRET` from the Meta app and use callback `https://socialpilot-ai-mvp.onrender.com/auth/facebook/callback`. Facebook Page posting is exposed at `POST /api/facebook/pages/posts`. Do not attempt Instagram connection while it remains pending.

Instagram remains disabled by request. Facebook Page OAuth needs a Meta app with the Page permissions and review required by Meta. Merely configuring credentials does not grant provider approval.

## Metricool-style Dashboard

Open `/dashboard` for a mobile-first workspace with service/configuration status, AI content and image generation, scheduling, post queue, recent Instagram engagement report, and shortcuts to the built-in editor and setup checklist. The dashboard uses the existing API; configure the server secrets, persistent database, OpenAI API access and Meta permissions before live actions will work.

## Built-in Post & Video Studio

Open `/studio` on the deployed service for the in-app mobile-friendly design editor. It includes editable text and shapes, image upload, 4:5/square/story/landscape canvas sizes, starter templates, drag-to-position, basic layer ordering, PNG export, local browser project save/load, JSON project export, and browser-native animated WebM export. The studio does not require a Canva account or design-app SDK. AI copy/image buttons reuse the configured server AI API and may incur usage charges. Current video export is WebM only and animates one design; multi-scene timelines, AI voice generation, and MP4 export are not implemented in this initial version.

## Multi-platform integrations and current status

The `/platforms` page lists Instagram, Facebook Pages, LinkedIn, YouTube, TikTok, Pinterest and X in one connection hub. Instagram is disabled/pending by request. Facebook Page text/link publishing, LinkedIn text publishing, YouTube resumable video upload, X text publishing, Pinterest image pins and TikTok URL-based video publishing have code in the repository. Every provider still requires its own credentials, permissions/approval, and end-to-end tests against a real account before publishing can be considered live. Do not show a channel as connected or claim publishing works until verified.

## Features implemented in code

- Instagram Login OAuth start/callback with encrypted PostgreSQL token storage.
- Existing Instagram queue code remains in the project but is not part of the active launch scope. Facebook Page text/link, LinkedIn text, X text, Pinterest image-pin and TikTok video publish endpoints are implemented in code; YouTube resumable video upload is also implemented. Provider credentials and live-account verification are still required.
- Mobile content planner with topic ideas, editable captions, scheduling and queue.
- AI content-package generation endpoint and planner control, using OpenAI when configured.
- Optional daily queue generation for two posts at 10:00 and 18:00 India time, with duplicate-attempt protection. Manual trigger: `POST /api/automation/queue-daily`. Background daily generation is OFF by default and requires `AUTO_CONTENT_ENABLED=true` and `INSTAGRAM_USER_ID`.
- AI image generation endpoint; generated image bytes are stored in PostgreSQL and exposed through a public HTTPS asset URL for Instagram to fetch.
- Recent Instagram media report with likes and comment counts.
- Instagram comment webhook verification and a webhook handler for AI-generated replies, with a database table to avoid replying to the same comment twice.
- ChatGPT MCP Instagram agent skill runner covering 13 workflows: Reels, research/swipe analysis, captions, carousels, Stories, profile audits, weekly planning, humanizing drafts, comment drafts, comment replies, opt-in DM drafts, repurposing, and performance audits. These generate drafts only; they do not post, comment, or send DMs.
- Customer account foundation with salted PBKDF2 password hashes and signed HttpOnly session cookies; signup is enabled in the current Render environment for testing; this is not yet a production onboarding approval.
- Session-authenticated customer APIs for workspace-scoped Instagram connections, content drafting, image uploads, scheduled-post listing and cancellation.
- GitHub Actions smoke tests.

## Go-live and sale-readiness checklist

Before selling this as a hosted SaaS, complete and verify all of the following: (1) a successful OAuth connection for each supported non-Instagram provider; (2) successful live test publishing on each provider and token refresh/expiry handling; (3) durable multi-platform scheduling while the service sleeps/restarts; (4) production verification of cross-workspace isolation, session expiry/revocation, rate limiting, email verification, usage limits and customer onboarding; (5) privacy policy, terms, data deletion and support process; (6) Meta webhook verification and permission review where needed; and (7) automated tests plus a full end-to-end test on the production deployment. Do not advertise features as live until their real integration test passes.

## Important limitations

This repository now contains code for these workflows, but **not every workflow is live/verified**. Actual use depends on Render environment settings, database setup, Meta app permissions, webhook subscriptions, OpenAI account access/credits, and end-to-end tests.

- AI text/image generation requires `OPENAI_API_KEY`; API use may incur charges. The default models are `gpt-4o-mini` and `gpt-image-1`, configurable via environment variables.
- Instagram publishing requires a saved long-lived token, an eligible Creator/Business account, public HTTPS image URLs, and Meta API permission/access.
- Auto-replies are OFF by default. To enable them, set `AUTO_REPLY_ENABLED=true`, configure `META_WEBHOOK_VERIFY_TOKEN`, add the webhook callback `https://socialpilot-ai-mvp.onrender.com/webhooks/instagram` in Meta, verify it, subscribe to the Instagram comments webhook field, and grant comment-management permission. Meta's app setup/review may be required.
- The report endpoint summarizes recent media and engagement counts; it does not yet provide a full growth dashboard or every Insights metric.
- This does not automatically create and queue two posts every day yet. Content generation and scheduling are available as separate operations.
- Generated images are stored in PostgreSQL; monitor database size and retention as usage grows.
- OAuth state is stored as a SHA-256 hash in PostgreSQL, expires after 15 minutes, and is consumed once. Instagram/Facebook OAuth therefore requires `DATABASE_URL` to be configured before starting login.

## Render environment variables

Set secrets in Render's Environment page. Never commit secrets or paste them into chat.

| Variable | Required for | Notes |
| --- | --- | --- |
| `META_APP_ID` | Facebook Page login | Meta app ID |
| `META_APP_SECRET` | Facebook Page login | Private app secret |
| `INSTAGRAM_REDIRECT_URI` | Legacy/pending Instagram route | Not used while Instagram connection remains disabled. |
| `DATABASE_URL` | Token storage, queue, generated assets | Persistent PostgreSQL connection URL |
| `TOKEN_ENCRYPTION_KEY` | Token storage | Valid Fernet key; keep stable and private |
| `AUTOMATION_API_KEY` | Planner API | Strong private key for schedule, AI and report endpoints |
| `OPENAI_API_KEY` | AI content/images and AI comment replies | Private API key; provider usage may be billed |
| `OPENAI_TEXT_MODEL` | Optional | Defaults to `gpt-4o-mini` |
| `OPENAI_IMAGE_MODEL` | Optional | Defaults to `gpt-image-1` |
| `APP_BASE_URL` | Generated image links | `https://socialpilot-ai-mvp.onrender.com` |
| `META_WEBHOOK_VERIFY_TOKEN` | Webhook verification | Choose a private value and use the same value in Meta |
| `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` | LinkedIn OAuth and text posts | LinkedIn developer app with OpenID Connect and `w_member_social` approved; callback `/auth/linkedin/callback` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | YouTube channel connection | Google OAuth client and YouTube Data API v3 enabled; callback `/auth/youtube/callback` |
| `YOUTUBE_REDIRECT_URI` | YouTube OAuth | Must exactly match Google Cloud OAuth client; defaults to `https://socialpilot-ai-mvp.onrender.com/auth/youtube/callback` |
| `X_CLIENT_ID` / `X_CLIENT_SECRET` | X OAuth and text posts | X developer app with OAuth 2.0 enabled; callback `/auth/x/callback` |
| `X_REDIRECT_URI` | X OAuth | Must exactly match X app callback; defaults to `https://socialpilot-ai-mvp.onrender.com/auth/x/callback` |
| `PINTEREST_APP_ID` / `PINTEREST_APP_SECRET` | Pinterest OAuth and pins | Pinterest developer app and approved scopes; callback `/auth/pinterest/callback` |
| `PINTEREST_REDIRECT_URI` | Pinterest OAuth | Must exactly match Pinterest app callback; defaults to `https://socialpilot-ai-mvp.onrender.com/auth/pinterest/callback` |
| `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` | TikTok OAuth and video publishing | TikTok developer app with Content Posting API approval; callback `/auth/tiktok/callback` |
| `TIKTOK_REDIRECT_URI` | TikTok OAuth | Must exactly match TikTok app callback; defaults to `https://socialpilot-ai-mvp.onrender.com/auth/tiktok/callback` |
| `AUTO_REPLY_ENABLED` | Auto-replies | Leave `false` until webhook verification and comment permission are tested |
| `AUTO_CONTENT_ENABLED` | Daily content queue | Leave `false` until AI and publishing have been tested; set `true` to queue the next day's two posts automatically |
| `INSTAGRAM_USER_ID` | Daily content queue | Connected Instagram account ID |

The Render Blueprint uses `sync: false` for private settings; that does not populate them automatically or provision PostgreSQL. If a token has already been saved, do not rotate `TOKEN_ENCRYPTION_KEY` without a migration plan.

## Endpoints

- `GET /health`
- `GET /diagnostics/oauth-config` — reports booleans only for private settings.
- `GET /api/automation/status` — reports feature configuration, not secret values.
- `GET /api/content/ideas`
- `POST /api/ai/generate` — header `X-Automation-Key`, JSON `{"topic":"..."}`
- `POST /api/ai/image` — header `X-Automation-Key`, JSON `{"prompt":"..."}`
- `POST /api/posts/schedule` and `GET /api/posts` — header `X-Automation-Key`
- `GET /api/reports/instagram?instagram_user_id=...` — header `X-Automation-Key`
- `GET/POST /webhooks/instagram` — Meta webhook verification and event receiver
- `GET /assets/{asset_id}` — generated public image asset for Instagram fetching

## Manual completion and verification checklist

1. Set the environment variables in Render and attach a persistent PostgreSQL database.
2. Ensure the Meta app's Instagram Login redirect URL exactly matches the callback above.
3. Confirm the Meta app has the needed permissions and the Instagram account is eligible.
4. Open `/platforms`, connect one non-Instagram channel whose credentials are configured, then verify a real test post on that platform.
5. Open `/api/automation/status` and verify the expected configuration booleans.
6. Open `/planner`, generate a sample caption and image, schedule a test post a few minutes in the future, and verify the post becomes `published`. The same page can queue tomorrow's two posts after configuration.
7. Configure and verify the Meta webhook while auto-replies remain disabled. Test with a controlled comment before setting `AUTO_REPLY_ENABLED=true`.
8. Check the report endpoint for recent posts.

## Development

```bash
pip install -r requirements.txt
pytest -q
```


## Razorpay monthly subscriptions (integration code added; not live yet)

Razorpay billing routes are available in code at `/billing`, `/api/billing/status`, `/api/billing/create-subscription`, and `/webhooks/razorpay`. The billing code has automated safety tests, but it is not active until merchant KYC/account approval, a monthly plan, API credentials, webhook configuration and a live/test-mode end-to-end test are completed. Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_PLAN_ID`, and `RAZORPAY_WEBHOOK_SECRET` in Render Environment. Do not share secrets in chat or commit them.

The subscription-creation route is admin-key protected for owner-led testing. **Customer self-service checkout and automatic paid-access enforcement are not implemented yet. Customer login/workspace APIs are in code but are not considered production-ready until the latest deploy and cross-workspace tests are verified. Do not sell subscriptions or grant customer access based only on a checkout URL.** Razorpay setup is intentionally pending until the owner is ready.


## Pinterest publishing

Pinterest OAuth and image-pin publishing routes are implemented at `/auth/pinterest/start`, `/auth/pinterest/callback`, and `POST /api/pinterest/pins`. Pin payloads require a Pinterest board ID, title, description, public HTTPS image URL, and optional destination link. Configure `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`, and matching `PINTEREST_REDIRECT_URI`; the app must be approved for the required API scopes. Real-account OAuth and pin publishing have not yet been verified.


## TikTok publishing

TikTok OAuth and URL-based video publishing routes are implemented at `/auth/tiktok/start`, `/auth/tiktok/callback`, and `POST /api/tiktok/videos`. The input requires a public HTTPS video URL, caption/title, and privacy level. Configure `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, and matching `TIKTOK_REDIRECT_URI`; TikTok requires Content Posting API approval, scope approval and URL-domain verification. The publish-init response is an accepted job, not proof the video is already public; check TikTok publish status before claiming success. Real-account OAuth and publishing have not been verified.


## YouTube video upload

`POST /api/youtube/videos` accepts multipart fields `video` (video file, max 256 MB), `title`, optional `description`, and `privacy_status` (`private` by default, or `unlisted` / `public`). It uses YouTube resumable upload and refreshes expired access tokens when a refresh token is stored. Configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI`, and enable YouTube Data API v3 with upload scope. Public publishing should only be enabled after account and processing tests. This endpoint is implemented in code but not yet tested with a real channel.


## Facebook Page publishing

Facebook Page OAuth uses `/auth/facebook/start` and `/auth/facebook/callback`. The callback saves the selected available Page token encrypted in the workspace `social_connections` table. `POST /api/facebook/pages/posts` accepts `{ "message": "...", "link": "https://..." }` with an authenticated customer session and publishes a text/link post to the connected Page. It requires `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts` access, plus any Meta app review required for the app. No live Page connection/post has been verified yet.


## Free AI Lip-Sync Studio

Open `/lipsync` on the deployed service to access a mobile-friendly workspace for the public MuseTalk 1.5 ZeroGPU demo. Upload a front-facing photo and Hindi voiceover, generate the talking video in the external demo, then pass the resulting MP4 to your Make.com publishing scenario. Inference is not executed on the Render CPU instance. The public free GPU demo may queue, be rate-limited, or be temporarily unavailable; verify the returned video before publishing. Uploaded media is processed by the external Hugging Face Space, so only upload media you have permission to use.
