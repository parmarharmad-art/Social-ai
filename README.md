# SocialPilot AI MVP

AI-powered social media automation starter for an Instagram Creator account, designed to be configured from an Android phone.

## Included
- FastAPI backend with Instagram Login OAuth start/callback routes.
- Environment-based configuration; real credentials must never be committed.
- Health endpoint and a basic dashboard page.

## Important limitations
This is a starter implementation, not a deployed or production-ready service. Meta app configuration, redirect URL registration, OAuth testing, secure token storage/refresh, background scheduling, media hosting, and actual publishing must be completed and tested before automation is considered working. Instagram publishing is subject to Meta permissions, account eligibility, and app review requirements.

## Setup
1. Create/configure a Meta developer app with Instagram API using Instagram Login.
2. Set the exact redirect URI to `https://YOUR_PUBLIC_HOST/auth/instagram/callback`.
3. Copy `.env.example` to `.env` locally and fill in values. Never commit `.env`.
4. Install dependencies and run:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
5. Open `/health` to check the service and `/auth/instagram/start` to begin login.

The OAuth callback intentionally does not persist tokens yet. Secure encrypted storage and production session/state handling are required before using this for automation.

Never paste app secrets, access tokens, or passwords into chat or GitHub.
