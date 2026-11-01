# Claude + Make handoff: book-summary Reels

## Purpose
This is an additional content lane for the existing @officialkiraankumar social-media automation. Claude and Make remain responsible for script refinement, faceless video production, scheduling/approval and the existing Instagram publishing integration. GitHub is the source of truth for the 30-day topic/content queue.

## Source endpoint
Use Make HTTP > Make a request:
- Method: GET
- URL: https://raw.githubusercontent.com/parmarharmad-art/Social-ai/main/social-content/book_summaries.json
- Parse response as JSON.
- Iterate the returned top-level array; each object is one Reel package.
- Use `id` as the idempotency key so a retry does not create a duplicate post.

## Claude input mapping
Pass these fields from the current iterator item:
`id, book, author, theme, hook, voiceover, scenes, caption, cta, hashtags`.

Claude's job:
1. Fact-check the proposed lesson against an authorised/legitimate source when available. If uncertain, label it as a general reflection rather than a direct claim from the book.
2. Preserve Hinglish and the faceless style.
3. Produce a 30–50 second original narration, scene-by-scene visual prompts and readable on-screen captions.
4. Keep the book and author attribution in the caption.
5. Never invent quotations, page numbers or claims of official endorsement.
6. Do not output long excerpts, audiobook transcripts, scanned-page reproductions or copied cover artwork.
7. Return structured JSON fields: `id, final_voiceover, scene_plan, on_screen_captions, instagram_caption, hashtags, rights_review, editorial_review`.

## Make scenario flow
1. Use the existing schedule/trigger; do not add a competing daily schedule.
2. HTTP GET the source JSON.
3. Parse JSON and iterate each item.
4. Check the idempotency key against the existing Make data store/log so the same ID is not processed twice.
5. Send the item to Claude using the mapping above.
6. Generate the faceless video with the existing video modules and licensed/owned visuals/audio.
7. Send the finished asset and caption through the existing founder approval gate.
8. After approval, hand off to the existing Instagram publishing module. Do not create or enable a second Instagram publisher.
9. Log published media ID/permalink, timestamp, content ID and outcome in the existing reporting destination.

## Suggested Claude system instruction
You are the Hinglish faceless book-learning Reel editor for @officialkiraankumar. Treat the supplied GitHub item as an editorial brief, not as permission to copy the book. Explain one verifiable idea in original simple Hinglish, give a relatable everyday example and one practical action. Keep the video 30–50 seconds, 9:16, faceless and accessible with concise captions. Preserve accurate book/author attribution. Do not invent quotes, page numbers, endorsements, statistics or book claims. Never reproduce long passages, audiobook content, scanned pages or unlicensed cover art. If the idea cannot be verified, mark it as a general reflection and flag it for human review. Return only the agreed JSON fields. Never publish; publishing is handled only by the existing Make approval/publishing flow.

## Important boundaries
- Do not change or replace the existing Instagram publishing connection, schedule, approval gate or analytics route.
- Do not assume a GitHub QA pass means the book content is factually verified or the Reel is ready to publish.
- The GitHub QA workflow only checks the content package structure. Claude/editorial review and human final-video approval remain required.
- The JSON endpoint is public because the repository is public. Do not put secrets, personal data, tokens, private Make webhook URLs or credentials in this repository.
