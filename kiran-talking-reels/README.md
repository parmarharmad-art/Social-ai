# Kiran Kumar • AI Talking Reels MVP

A mobile-friendly Streamlit app that converts a photo plus Hindi narration into a vertical MP4, with a brand watermark and caption export.

## Important limitation
This MVP creates a photo-led narrated Reel with subtle zoom. It does NOT animate lips or provide verified talking-photo output. Lip-sync requires a separately selected hosted API or GPU engine. Check current commercial licensing, pricing, consent rules, and hardware before selecting one. Instagram publishing is not implemented.

## Features
- Upload JPG/PNG/WEBP photo and enter topic or script.
- Basic Hindi/Hinglish script draft.
- Hindi TTS through gTTS (internet required), or upload recorded narration.
- 1080x1920 H.264/AAC MP4 render through FFmpeg.
- Watermark, caption and script download.
- Basic file/stream validation and pytest checks.

## Local setup
Python 3.11 recommended. FFmpeg must be available as the command ffmpeg.
1. Create environment: python -m venv .venv
2. Activate it.
3. Install: pip install -r requirements.txt
4. Run: streamlit run app.py
5. Open the displayed app URL, upload a photo, enter topic, review script, generate.

gTTS requires internet access. Review its terms before commercial or sensitive use.

## Android-friendly deployment
Use GitHub to store code and a cloud host that supports Streamlit, FFmpeg, and sufficient runtime. Phone-only use can operate the hosted UI, but rendering happens on the host. GPU lip-sync usually needs a separate GPU worker or paid provider; free CPU hosting can sleep, time out, or lack FFmpeg. Never commit API keys.

## Tests
Run pytest -q. Included tests cover image validation and basic script/caption helpers. They do not verify external TTS, actual video render, lip-sync, subtitles, or Instagram publishing.

## Example
Topic: WhatsApp lead follow-up automation
Hook idea: “क्या आप leads को follow-up करना भूल जाते हैं?”
Review the generated caption, spelling, face framing, audio and duration before posting.

## Known limitations and next steps
- No word-timed subtitles, lip-sync, blinking, head motion, or B-roll.
- Background music mix is basic and needs manual review.
- Script generation is template-based, not live researched.
- Instagram publishing and analytics are not implemented.
- Test an actual render on the chosen host before calling it production-ready.
