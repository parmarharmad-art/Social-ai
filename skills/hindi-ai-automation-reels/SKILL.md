---
name: hindi-ai-automation-reels
description: Generate premium, research-driven Hindi Instagram Reels about practical AI automation, with Devanagari narration, subtitles, Python-based production requirements, and strict quality checks.
---

# MANDATORY HINDI REEL GENERATION

## Language Rules
- All Reel scripts must be written in natural, conversational Hindi.
- Use Devanagari script for spoken narration and Hindi subtitles.
- Keep technical tool names in their official English spelling: ChatGPT, Claude, Python, Make, Zapier, n8n, MCP, Google Sheets, Meta Ads.
- Explain technical concepts in simple Hindi that Indian beginners can understand.
- Avoid robotic translations, overly formal Hindi, and unnecessary English sentences.
- Use natural Indian speaking rhythm and pronunciation.
- Use Hinglish only for commonly understood technical terms where translating them would reduce clarity.

## Hindi Voice-Over
- Generate clear, natural-sounding Hindi narration.
- Use a compatible Hindi TTS voice or an authorized human voice recording.
- Configure Hindi language and voice settings explicitly.
- Pronounce tool names and technical abbreviations clearly.
- Match narration timing to the scene and subtitle timing.
- If Hindi TTS is unavailable, report the limitation rather than silently generating English audio.

## Hindi Subtitles
- Generate subtitles in Devanagari.
- Use a font that supports Hindi characters, such as Noto Sans Devanagari.
- Check matras, conjunct letters, punctuation, and line breaks.
- Keep subtitles readable on mobile screens and within vertical-video safe areas.
- Synchronize subtitles with actual narration.
- Do not leave English placeholder subtitles in a Hindi Reel.

## Hindi Script Structure
Every Reel must include:
1. पहले 1–3 सेकंड में एक दमदार शुरुआत।
2. दर्शक की असली समस्या।
3. आसान हिंदी में व्यावहारिक समाधान।
4. स्क्रीन पर वास्तविक वर्कफ़्लो या स्पष्ट उदाहरण।
5. परिणाम की जाँच और ज़रूरी सीमाएँ।
6. स्वाभाविक हिंदी में एक प्रासंगिक CTA।

## Python Implementation
- Save scripts as UTF-8.
- Use a Hindi-capable font for all rendered graphics.
- Verify Devanagari text rendering before producing the batch.
- Use a compatible Hindi TTS engine and check its availability before rendering.
- Export videos in vertical 9:16 format, targeting 1080 × 1920.
- Verify that Hindi narration, subtitles, and on-screen text match the approved script.
- Include the Hindi caption, cover image, and final MP4 for every Reel.

## Quality Gate
Do not approve a Reel if:
- Narration is in English instead of Hindi.
- Devanagari characters render incorrectly.
- Subtitles are missing or unsynchronized.
- Tool names or technical instructions are incorrect.
- The content is generic, repetitive, or unsupported by evidence.

The final delivery must contain Hindi Reels, Hindi voice-over, Hindi subtitles, and Hindi captions for all approved topics.

## Python Video Production Requirements
- Build the video from approved scripts using Python and compatible tools such as MoviePy, FFmpeg, and Pillow.
- Verify installed library versions and document dependencies in `requirements.txt`.
- Generate actual MP4 files, not just scripts, storyboards, or placeholder clips.
- Check output duration, resolution, audio presence, subtitle rendering, and successful decoding.
- If a video cannot be generated because a dependency, voice service, or API is unavailable, report the exact blocker rather than claiming success.
- Package verified MP4s, matching captions, covers, a content-plan CSV, and a quality-control report into a ZIP only after checking the files.

## Brand and Originality
- Brand: Kiran Kumar • AI Automation
- Instagram: @officialkiraankumar
- Create original, practical, evidence-based content. Avoid generic AI tips, invented statistics, fabricated client results, and misleading claims.
- Use the user's actual reference photo in presenter-based videos when supplied and supported by the tools. Preserve identity; change clothing, pose, framing, and background only without creating a different face. If identity consistency cannot be verified, use voice-over and workflow visuals instead of a lookalike.
- Never promise virality or guaranteed follower growth.
