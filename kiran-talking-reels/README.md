# Kiran Kumar • AI Talking Reels

A mobile-friendly Flask web app for producing vertical photo-led Hindi/Hinglish narration Reels. Upload a photo, draft or edit a script, create narration or upload your own audio, add optional background music, and export MP4, caption, script, and SRT subtitle files.

## Included
- JPG/PNG/WEBP upload and image validation.
- Hindi/Hinglish topic-to-script generation and Instagram caption.
- gTTS narration (internet required) or uploaded recorded narration.
- Vertical 720×1280 H.264/AAC MP4 render using FFmpeg.
- Optional genuine mouth lip-sync through the public free MuseTalk ZeroGPU Space; no HeyGen API key or paid lip-sync API is used.
- Faster photo-zoom + narration fallback if you choose it.
- “Kiran Kumar | AI Automation” watermark and approximate SRT captions.
- Downloadable MP4, script, caption, and SRT sidecar.
- Automated unit tests and GitHub Actions CI.

## Important limitations
The free MuseTalk integration depends on a public third-party Space and its free GPU queue/quota. It can be busy, asleep, changed, or unavailable; it is not an unlimited or guaranteed always-on service. If it fails, the app should show an error rather than falsely label a still-photo video as lip-synced. Subtitles are approximate sentence/phrase timings, not word-level speech recognition. Instagram auto-publishing and analytics are not implemented in this Reel Studio. Review every output before publishing.

## Run locally
1. Install Python 3.11+ and FFmpeg.
2. From this folder, run:
   ```bash
   python -m venv .venv
   # Activate the virtual environment, then:
   pip install -r requirements.txt
   python app.py
   ```
3. Open the local URL, upload a photo, add a topic/script, select narration, and press **Generate Reel**.

gTTS requires internet access. For sensitive or commercial voice work, review its terms and consider using a properly licensed voice provider.

## Cloud deployment from an Android phone
A Docker-capable host is recommended because the app needs FFmpeg and Hindi-capable fonts.

1. In your host's dashboard, create a new **Docker web service** from `parmarharmad-art/Social-ai`.
2. Set **Root Directory** to `kiran-talking-reels`.
3. Set Dockerfile path to `Dockerfile` (or leave the default for the root directory).
4. Deploy. The container reads the host's `PORT` variable and runs Streamlit.
5. Upload a test image and render a short 15-second Reel to verify CPU, memory, fonts, and FFmpeg support before using longer durations.

Free web services may sleep, have short request timeouts, or lack sufficient memory for video rendering. Generated files are stored in the service filesystem and may disappear on redeploy/restart unless persistent storage is configured. Do not commit API keys or private photos.

## Tests
Run `pytest -q` from this folder. Tests cover image validation, script/caption helpers, and SRT generation. They do not prove that cloud video rendering, TTS, or external services work in every host environment.

## Next integration work
- Licensed photo-to-talking-head/lip-sync provider or GPU inference worker.
- Accurate subtitles from speech recognition and audio timing.
- Real B-roll generation and transition templates.
- Instagram Graph API publishing and insights, after Meta app review, permissions, and account configuration.
