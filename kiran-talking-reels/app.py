import shutil
import subprocess
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.hindi_tts import make_audio
from src.script_generator import make_caption, make_script
from src.subtitles import make_srt
from src.validation import ffprobe_info, validate_image
from src.video_renderer import render

load_dotenv()
ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


st.set_page_config(page_title="Kiran Kumar • AI Talking Reels", page_icon="🎬")
st.title("🎬 Kiran Kumar • AI Talking Reels")
st.caption("Kiran Kumar • AI Automation")
st.info("This version creates a narrated photo Reel with a slow zoom, branding, and timed sentence subtitles when supported by FFmpeg. True realistic lip-sync/blinking/head motion needs a configured external AI service or GPU model.")
photo = st.file_uploader("Upload your photo", type=["jpg", "jpeg", "png", "webp"])
topic = st.text_input("Reel topic", placeholder="WhatsApp lead follow-up automation")
duration = st.select_slider("Target duration (seconds)", options=[15, 30, 45, 60], value=30)
language = st.selectbox("Language", ["Hindi", "Hinglish"])
script = st.text_area("Review or edit your script", height=150)
voice = st.radio("Narration source", ["Generate Hindi voice (internet required)", "Upload recorded voiceover"])
audio_upload = st.file_uploader("Voiceover audio", type=["mp3", "wav", "m4a"]) if voice.startswith("Upload") else None
music = st.file_uploader("Optional background music", type=["mp3", "wav", "m4a"])

if st.button("Generate Reel", type="primary"):
    if not photo:
        st.error("Upload a photo first.")
    elif not topic.strip() and not script.strip():
        st.error("Enter a topic or script.")
    else:
        work = Path(tempfile.mkdtemp(prefix="kiran_reel_"))
        try:
            img = work / "photo.png"
            img.write_bytes(photo.getvalue())
            validate_image(img)

            final_script = script.strip() or make_script(topic, duration, language)
            st.subheader("Script preview")
            st.write(final_script)
            (OUT / "latest_script.txt").write_text(final_script, encoding="utf-8")
            srt_content = make_srt(final_script, duration)
            subtitle_file = work / "captions.srt"
            subtitle_file.write_text(srt_content, encoding="utf-8")
            (OUT / "captions.srt").write_text(srt_content, encoding="utf-8")

            audio = work / "voice.mp3"
            if voice.startswith("Upload"):
                if not audio_upload:
                    raise ValueError("Upload a recorded voiceover.")
                audio.write_bytes(audio_upload.getvalue())
            else:
                make_audio(final_script, audio)

            music_path = None
            if music:
                music_path = work / ("music" + Path(music.name).suffix.lower())
                music_path.write_bytes(music.getvalue())

            output = OUT / "kiran_talking_reel.mp4"
            render(img, audio, output, duration, subtitle_file, music_path)
            info = ffprobe_info(output)
            st.success("MP4 rendered and basic video stream validation passed.")
            st.video(str(output))
            st.download_button("Download MP4", output.read_bytes(), "kiran_talking_reel.mp4", "video/mp4")
            caption = make_caption(topic or "AI workflow", final_script)
            st.text_area("Instagram caption", caption, height=150)
            st.download_button("Download caption", caption, "caption.txt", "text/plain")
            st.download_button("Download script", final_script, "hindi_script.txt", "text/plain")
            st.download_button("Download subtitles (SRT)", srt_content, "captions.srt", "application/x-subrip")
            st.json(info)
            st.warning("Review audio, subtitle timing, face framing, pronunciation, and duration before posting. Lip-sync is not implemented.")
        except Exception as exc:
            st.error(f"Generation failed: {exc}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
