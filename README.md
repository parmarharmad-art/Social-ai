# SocialPilot AI MVP

AI-powered social media automation starter for an Instagram Creator account, designed to be configured from an Android phone.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/parmarharmad-art/Social-ai)

**Quick deploy:** tap the button above (or open [this deployment link](https://render.com/deploy?repo=https://github.com/parmarharmad-art/Social-ai)), sign in to Render if asked, connect GitHub if asked, then review and approve the Blueprint. Render will ask you to provide Meta app environment values; deployment alone does not connect Instagram.

## Included
- FastAPI backend with Instagram Login OAuth start/callback routes.
- Environment-based configuration; real credentials must never be committed.
- Health endpoint and a basic dashboard page.
- Automated smoke tests via GitHub Actions.

## Important limitations
This is a starter implementation, not a deployed or production-ready service. Meta app configuration, redirect URL registration, OAuth testing, secure token storage/refresh, background scheduling, media hosting, and actual publishing must be completed and tested before automation is considered working. Instagram publishing is subject to Meta permissions, account eligibility, and app review requirements.

## Setup
1. Create/configure a Meta developer app with Instagram Login.
2. After Render provides the service URL, set the exact redirect URI to `https://YOUR-SERVICE.onrender.com/auth/instagram/callback` in the Meta app and as `INSTAGRAM_REDIRECT_URI` in Render.
3. Set `META_APP_ID` and `META_APP_SECRET` in Render's environment settings. Never commit secrets to GitHub or paste them into chat.
4. Open `https://YOUR-SERVICE.onrender.com/health` to check the service and `/auth/instagram/start` to begin login.
5. Run tests locally with `pytest -q`; GitHub Actions also runs them on pushes and pull requests.

The OAuth callback intentionally does not persist tokens yet. Secure encrypted storage and production session/state handling are required before using this for automation.

Never paste app secrets, access tokens, or passwords into chat or GitHub.
