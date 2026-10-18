# Social Media Automation Skills

Reusable agent skills for the Social-ai repository. Each skill is stored in its own folder as a SKILL.md file.

## Skills
- [Social Media Strategy](social-media-strategy/SKILL.md) — audience, goals, content pillars, channel plans, and calendars.
- [Social Content Production](social-content-production/SKILL.md) — posts, carousels, captions, creative briefs, and scripts.
- [Social Publishing Automation](social-publishing-automation/SKILL.md) — scheduling, API validation, idempotency, approvals, and safe publishing.
- [Social Analytics and Optimization](social-analytics-optimization/SKILL.md) — metrics, reporting, experiments, and evidence-led optimization.
- [Community Management](community-management/SKILL.md) — comment/DM triage, reply drafts, lead routing, and escalation.
- [Short-Form Video](short-form-video/SKILL.md) — Reels/Shorts scripts, subtitles, render checks, and lip-sync validation.
- [Social Automation Engineering](social-automation-engineering/SKILL.md) — pipeline reliability, CI safety, logs, retries, secrets, and artifact verification.

## Operating principles
- Start in draft/dry-run mode. Live publishing, deleting, boosting, or sending messages requires explicit authorization.
- Never commit credentials or expose tokens in logs.
- Do not claim an asset or workflow succeeded until the output is verified.
- Use the platform's official APIs and follow current permissions, rate limits, and policies.
- Keep changes scoped and preserve existing user content.
