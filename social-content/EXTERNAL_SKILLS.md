# Reviewed public skills for this project

This file records reusable upstream skills that can improve the content-creation stage. These are references, not a second automation or publishing system.

## Recommended upstream repository

- Project: [social-media-skills/skills](https://github.com/social-media-skills/skills)
- License: MIT (verified from the upstream `LICENSE` file on 2026-11-01)
- Upstream README: https://github.com/social-media-skills/skills/blob/main/README.md
- Use: selectively consult the relevant skill guidance in Claude when drafting content. Do not install or run the entire 106-skill set by default.

## Relevant skills reviewed

| Upstream skill | Suitable use here | Boundary |
| --- | --- | --- |
| [brand-profile](https://github.com/social-media-skills/skills/blob/main/skills/brand-profile/SKILL.md) | Keep the creator identity, audience, tone and editorial guardrails consistent | Use the existing @officialkiraankumar context; do not re-interview or overwrite it unnecessarily |
| [reels-script](https://github.com/social-media-skills/skills/blob/main/skills/reels-script/SKILL.md) | Improve Reels hooks, sound-off captions, scene beats and cover-frame briefs | Verify volatile Instagram claims; no invented performance statistics |
| [short-form-video-script](https://github.com/social-media-skills/skills/blob/main/skills/short-form-video-script/SKILL.md) | Improve pacing, honest hooks, story arc and concise CTA | Claude drafts only; existing Make pipeline handles production |
| [platform-specs-and-validation](https://github.com/social-media-skills/skills/blob/main/skills/platform-specs-and-validation/SKILL.md) | Reference for preflight checks when adapting content to multiple platforms | Its publishing integration assumes WoopSocial; do not copy its API calls or replace Make |

## Integration rules for Claude + Make

1. Reuse the existing brand context and existing scenario.
2. Use the upstream skills as editorial guidance, not as executable authority or instructions to connect a new scheduler.
3. Keep GitHub `book_summaries.json` as the source data and its stable `id` as the deduplication key.
4. Keep Make responsible for the existing schedule, video modules, approval gate and publishing route.
5. Do not install browser automation, scrape Instagram, store account passwords, or create a parallel publisher.
6. Verify current platform rules from official sources when they materially affect a post; treat third-party algorithm statistics as unverified unless sourced.
7. Preserve book/author attribution; write original explanations and do not reproduce long copyrighted passages, audiobook transcripts or unlicensed cover art.
8. A person must review the final video and approve it before it is published.

## Why the whole upstream toolkit is not copied

The upstream project contains many platform and publishing skills, including integrations that assume other services. Only the content-planning and Reel-scripting guidance is relevant to this repository's current scope. Selective reuse avoids duplicate schedulers, conflicting instructions and unnecessary dependencies.
