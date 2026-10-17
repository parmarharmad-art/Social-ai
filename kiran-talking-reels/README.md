# Kiran Kumar • AI Talking Reels

A mobile-friendly Streamlit app for producing vertical photo-led Hindi/Hinglish narration Reels. Upload a photo, draft or edit a script, create narration or upload your own audio, add optional background music, and export MP4, caption, script, and SRT subtitle files.

## Included
- JPG/PNG/WEBP upload and image validation.
- Hindi/Hinglish template script and Instagram caption.
- gTTS narration (internet required) or uploaded recorded narration.
- 1080×1920 H.264/AAC video render using FFmpeg.
- Slow photo zoom, “Kiran Kumar | AI Automation” watermark.
- Approximate sentence-level SRT captions, with burn-in when FFmpeg has libass support.
- Downloadable MP4, script, caption, and SRT sidecar.
- Automated unit tests and GitHub Actions CI.

## Important limitations
This is **not yet a realistic talking-head generator**. It does not animate the mouth, blink, move the head, or generate real B-roll. Subtitles are sentence/phrase-timed estimates spread over the selected duration, not speech-recognition word-level timings. No Instagram auto-publishing or analytics are implemented. Those features require additional provider integrations, permissions, and credentials. Do not treat a video as ready to publish without reviewing it.

## Run locally
1. Install Python 3.11+ and FFmpeg.
2. From this folder, run:
   ```bash
   python -m venv .venv
   # Activate the virtual environment, then:
   pip install -r requirements.txt
   streamlit run app.py
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
