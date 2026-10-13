# GitHub Actions free daily automation setup

This repository includes a scheduled workflow at `.github/workflows/free-daily-automation.yml`.

## What it does

- Runs every day at 09:00 India time (GitHub scheduled workflows can start late).
- Calls the configured SocialPilot API health endpoint.
- Requests two AI-generated Instagram posts for the next day (scheduled by the API for 10:00 and 18:00 India time).
- Can also be run manually from GitHub Actions.

## Required repository secrets

Open the repository on GitHub, then **Settings → Secrets and variables → Actions → New repository secret**. Add these three secrets. Never put their values in code or commit them.

| Secret name | Value |
| --- | --- |
| `SOCIALPILOT_BASE_URL` | Base URL of the running SocialPilot API, without a trailing slash, e.g. `https://socialpilot-ai-mvp.onrender.com` |
| `SOCIALPILOT_AUTOMATION_KEY` | The same private `AUTOMATION_API_KEY` configured on the API server |
| `INSTAGRAM_USER_ID` | The numeric Instagram user ID connected to SocialPilot |

The API server must also have working `DATABASE_URL`, `TOKEN_ENCRYPTION_KEY`, `OPENAI_API_KEY`, and a saved Instagram token. The Instagram account must have the required Meta permissions.

## Run it manually

1. Open **Actions** in the repository.
2. Select **Free Daily Instagram Queue**.
3. Tap **Run workflow** → **Run workflow**.
4. Open the run and inspect the final step output. It must return `ok: true` and two posts. A failed run shows the API error in the logs; secret values are masked by GitHub.

## Important limitation

GitHub Actions provides the free scheduled trigger, not a continuously running web server. This workflow calls the API at `SOCIALPILOT_BASE_URL`; it does **not** replace the API server, persistent PostgreSQL database, Instagram OAuth callback, or Meta webhook endpoint. If the Render service is deleted/stopped or its free quota is exhausted, this workflow cannot create/publish posts. GitHub cron timing is best-effort, not exact-to-the-minute. AI generation may incur OpenAI charges.
