# SocialPilot AI MVP

Mobile-first Instagram automation project for **Kiran Kumar • AI Automation**.

- Repository: https://github.com/parmarharmad-art/Social-ai
- Render service: https://socialpilot-ai-mvp.onrender.com
- Planner: https://socialpilot-ai-mvp.onrender.com/planner

## Features implemented in code

- Instagram Login OAuth start/callback with encrypted PostgreSQL token storage.
- Scheduled Instagram image publishing queue and status tracking.
- Mobile content planner with topic ideas, editable captions, scheduling and queue.
- AI content-package generation endpoint and planner control, using OpenAI when configured.
- Optional daily queue generation for two posts at 10:00 and 18:00 India time, with duplicate-attempt protection. Manual trigger: `POST /api/automation/queue-daily`. Background daily generation is OFF by default and requires `AUTO_CONTENT_ENABLED=true` and `INSTAGRAM_USER_ID`.
- AI image generation endpoint; generated image bytes are stored in PostgreSQL and exposed through a public HTTPS asset URL for Instagram to fetch.
- Recent Instagram media report with likes and comment counts.
- Instagram comment webhook verification and a webhook handler for AI-generated replies, with a database table to avoid replying to the same comment twice.
- GitHub Actions smoke tests.

## Important limitations

This repository now contains code for these workflows, but **not every workflow is live/verified**. Actual use depends on Render environment settings, database setup, Meta app permissions, webhook subscriptions, OpenAI account access/credits, and end-to-end tests.

- AI text/image generation requires `OPENAI_API_KEY`; API use may incur charges. The default models are `gpt-4o-mini` and `gpt-image-1`, configurable via environment variables.
- Instagram publishing requires a saved long-lived token, an eligible Creator/Business account, public HTTPS image URLs, and Meta API permission/access.
- Auto-replies are OFF by default. To enable them, set `AUTO_REPLY_ENABLED=true`, configure `META_WEBHOOK_VERIFY_TOKEN`, add the webhook callback `https://socialpilot-ai-mvp.onrender.com/webhooks/instagram` in Meta, verify it, subscribe to the Instagram comments webhook field, and grant comment-management permission. Meta's app setup/review may be required.
- The report endpoint summarizes recent media and engagement counts; it does not yet provide a full growth dashboard or every Insights metric.
- This does not automatically create and queue two posts every day yet. Content generation and scheduling are available as separate operations.
- Generated images are stored in PostgreSQL; monitor database size and retention as usage grows.
- OAuth state currently resides in process memory, so production hardening should move state to a persistent secure store.

## Render environment variables

Set secrets in Render's Environment page. Never commit secrets or paste them into chat.

| Variable | Required for | Notes |
| --- | --- | --- |
| `META_APP_ID` | Instagram login | Meta app ID |
| `META_APP_SECRET` | Instagram login | Private app secret |
| `INSTAGRAM_REDIRECT_URI` | Instagram login | Must exactly match Meta: `https://socialpilot-ai-mvp.onrender.com/auth/instagram/callback` |
| `DATABASE_URL` | Token storage, queue, generated assets | Persistent PostgreSQL connection URL |
| `TOKEN_ENCRYPTION_KEY` | Token storage | Valid Fernet key; keep stable and private |
| `AUTOMATION_API_KEY` | Planner API | Strong private key for schedule, AI and report endpoints |
| `OPENAI_API_KEY` | AI content/images and AI comment replies | Private API key; provider usage may be billed |
| `OPENAI_TEXT_MODEL` | Optional | Defaults to `gpt-4o-mini` |
| `OPENAI_IMAGE_MODEL` | Optional | Defaults to `gpt-image-1` |
| `APP_BASE_URL` | Generated image links | `https://socialpilot-ai-mvp.onrender.com` |
| `META_WEBHOOK_VERIFY_TOKEN` | Webhook verification | Choose a private value and use the same value in Meta |
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
4. Open `/auth/instagram/start`, authorize, and confirm the callback says `token_saved: true`.
5. Open `/api/automation/status` and verify the expected configuration booleans.
6. Open `/planner`, generate a sample caption and image, schedule a test post a few minutes in the future, and verify the post becomes `published`. The same page can queue tomorrow's two posts after configuration.
7. Configure and verify the Meta webhook while auto-replies remain disabled. Test with a controlled comment before setting `AUTO_REPLY_ENABLED=true`.
8. Check the report endpoint for recent posts.

## Development

```bash
pip install -r requirements.txt
pytest -q
```
