---
name: social-publishing-automation
description: Design reliable, approval-aware scheduling and publishing workflows for supported social platforms.
---

# Social Publishing Automation

## Safety first
Publishing is an external side effect. Do not publish, delete, boost, or message audiences unless explicitly authorized and the target account, content, schedule, and timezone are clear. Prefer draft or dry-run mode until credentials and permissions are verified.

## Workflow
1. Inventory platforms, account types, scopes, supported media, API limitations, rate limits, and approvals.
2. Normalize posts into a schema: id, platform, account, media, caption, alt_text, scheduled_at with timezone, status, approval, idempotency_key, published_url, and error.
3. Validate media, duration, dimensions, file size, caption length, permissions, and schedule.
4. Use states such as draft -> approved -> queued -> publishing -> published or failed. Persist attempt count and provider response safely.
5. Make retries idempotent. After timeouts, reconcile provider status before retrying to avoid duplicate posts.
6. Keep tokens in repository secrets or a secret manager, never in code, logs, commits, or artifacts.
7. Implement bounded retries, backoff, rate-limit handling, useful logs, and manual recovery.
8. Use dry-run by default in CI. Require an explicit flag and approval gate for live publishing.
9. Report platform, post id, result, timestamp, permalink, and actionable sanitized errors.

## GitHub Actions
- Use least-privilege permissions and trusted action versions.
- Never print environment variables or tokens.
- Use concurrency controls to prevent overlapping publishing runs.
- Test on fixtures before enabling scheduled live runs.
