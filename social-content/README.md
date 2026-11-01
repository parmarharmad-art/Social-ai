# Social content repository guide

This folder is the GitHub source of truth for reusable social-content briefs. It does not schedule, render, approve or publish posts.

## Book-summary Reels lane

| Asset | Purpose |
| --- | --- |
| [book_summaries.json](book_summaries.json) | 30 original Hinglish, faceless Reel briefs |
| [30_DAY_BOOK_REELS_CALENDAR.md](30_DAY_BOOK_REELS_CALENDAR.md) | 30-day posting calendar with all captions, hashtags, hooks, CTAs and review checklist |
| [validate_book_summaries.py](validate_book_summaries.py) | Checks package structure, required fields, IDs, hooks and scene count |
| [BOOK_SUMMARY_REELS.md](BOOK_SUMMARY_REELS.md) | Editorial format, Android production notes and rights safeguards |
| [book-summary-make-config.json](book-summary-make-config.json) | Machine-readable source and field-mapping contract for Make |
| [BOOK_SUMMARY_MAKE_HANDOFF.md](BOOK_SUMMARY_MAKE_HANDOFF.md) | Claude + Make integration handoff and boundaries |
| [EXTERNAL_SKILLS.md](EXTERNAL_SKILLS.md) | Reviewed MIT-licensed public skills and safe reuse guidance |
| [book-summary-reels.yml](../.github/workflows/book-summary-reels.yml) | GitHub Actions QA workflow |

## Integration contract

- Public source JSON: https://raw.githubusercontent.com/parmarharmad-art/Social-ai/main/social-content/book_summaries.json
- Each record has a stable `id`; use it as the deduplication key.
- Claude may refine the narration and scene plan, but must preserve accurate attribution and avoid invented quotations or unsupported claims.
- Make owns the existing trigger/schedule, production modules, approval routing and publishing. Reuse those existing modules; do not create a second publisher or competing schedule.
- Keep credentials, tokens, private webhook URLs and personal data out of this public repository.

## Quality checks

The `book-summary-reels` GitHub Actions workflow runs the deterministic validator when the source data or validator changes, and can also be run manually. A passing check confirms data structure only; it is not a factual, copyright, video-quality or publishing approval.

## Change process

1. Edit the JSON package(s) and keep IDs stable unless replacing a content item.
2. Run `python social-content/validate_book_summaries.py` locally, or rely on the GitHub Actions check.
3. Review the Actions result and fix any validation errors.
4. Claude + Make handle the downstream workflow using the handoff contract.
