# SocialPilot AI MVP

A mobile-friendly Instagram Creator account automation MVP for **Kiran Kumar • AI Automation**.

Repository: https://github.com/parmarharmad-art/Social-ai  
Render service: https://socialpilot-ai-mvp.onrender.com

## What is in this repository

- FastAPI service with a health check at `/health`.
- Instagram Login OAuth start/callback routes.
- Long-lived Instagram token exchange and encrypted PostgreSQL token storage (requires Render environment configuration).
- A mobile content planner at `/planner`.
- A topic-ideas API at `/api/content/ideas`.
- A protected post scheduling API at `/api/posts/schedule` and queue API at `/api/posts`.
- A background publisher that checks scheduled posts every 30 seconds when PostgreSQL and a valid Fernet encryption key are configured.
- GitHub Actions smoke tests on pushes and pull requests.

## Important: current MVP limitations

This is **not yet a fully autonomous AI content creator**. Topic ideas and captions are currently templates; an AI model and image-generation provider have not been integrated. The planner requires a publicly reachable HTTPS image URL. It does not upload images itself.

Instagram publishing has not been confirmed end-to-end in production. Successful OAuth alone is not enough: token storage, database connectivity, the account's permissions, and an actual scheduled publishing test must all succeed. Publishing is subject to Meta's API rules, account eligibility, permissions, and app-review requirements.

## Render configuration checklist

Set these values in the Render service's Environment settings. Never commit secrets to this repository or paste them into chat.

| Variable | Purpose |
| --- | --- |
| `META_APP_ID` | Meta/Instagram app ID |
| `META_APP_SECRET` | Secret for the Meta/Instagram app |
| `INSTAGRAM_REDIRECT_URI` | Exact callback URL registered in the Meta developer app: `https://socialpilot-ai-mvp.onrender.com/auth/instagram/callback` |
| `DATABASE_URL` | Connection URL for a persistent PostgreSQL database |
| `TOKEN_ENCRYPTION_KEY` | Valid Fernet key used to encrypt stored Instagram tokens; keep it stable and private |
| `AUTOMATION_API_KEY` | A strong private key required by the planner's scheduling and queue endpoints |

The app accepts either `INSTAGRAM_APP_ID` / `INSTAGRAM_APP_SECRET` or the `META_APP_ID` / `META_APP_SECRET` aliases. Use one consistent pair. Do not rotate the encryption key after tokens have been saved unless you have a planned migration, because old tokens would become unreadable.

The Render Blueprint declares several values as `sync: false`; that only asks Render to collect them. It does not create the database or fill in private values automatically.

## How to use after Render is configured

1. Open `https://socialpilot-ai-mvp.onrender.com/health`; expect a JSON response with status `ok`.
2. Open `https://socialpilot-ai-mvp.onrender.com/diagnostics/oauth-config`. This shows whether the app secret, database URL, and encryption key are configured; it does not reveal their values.
3. Open `https://socialpilot-ai-mvp.onrender.com/auth/instagram/start` and complete Instagram authorization.
4. The callback should return `connected: true` and `token_saved: true` only when the long-lived token was encrypted and saved to PostgreSQL.
5. Open `https://socialpilot-ai-mvp.onrender.com/planner`. Enter the private automation key, choose a topic, supply a public HTTPS image URL, confirm the Instagram user ID, and schedule a test post for a future time.
6. Refresh the post queue and verify the post becomes `published` with an Instagram media ID. If it becomes `failed`, inspect the error without sharing any access tokens or secrets.

## Development and tests

Install dependencies and run:

```bash
pip install -r requirements.txt
pytest -q
```

GitHub Actions runs the test suite on pushes and pull requests.

## Security notes

- Do not commit app secrets, database credentials, access tokens, encryption keys, or the automation key.
- The planner sends the automation key to this service over HTTPS and does not intentionally save it in browser storage.
- Keep the Render service and dependencies updated.
- This MVP's OAuth state is held in process memory; a multi-instance or restart-resilient production deployment should use a secure shared session/state store.
