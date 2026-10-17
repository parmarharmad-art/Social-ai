import shutil
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

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_AUDIO_BYTES = 30 * 1024 * 1024
MAX_MUSIC_BYTES = 15 * 1024 * 1024

st.set_page_config(page_title="Kiran Kumar • AI Reels Studio", page_icon="🎬", layout="centered")
st.title("🎬 Kiran Kumar • AI Reels Studio")
st.caption("Create a vertical Hindi/Hinglish narrated photo Reel")
st.markdown("**By Kiran Kumar • AI Automation**")
with st.expander("Before you start — important limitations"):
    st.write(
        "This version creates a photo-led narrated Reel with a slow zoom, branding, and approximate "
        "sentence-level subtitles. It does not animate lips, blink, move the head, generate B-roll, "
        "or publish directly to Instagram. Check the result before posting."
    )
    st.write("Uploaded photos and audio are processed in a temporary job folder and are not intentionally saved as shared output files.")
photo = st.file_uploader("1. Upload a photo (JPG, PNG or WEBP; up to 10 MB)", type=["jpg", "jpeg", "png", "webp"])
topic = st.text_input("2. Reel topic", placeholder="WhatsApp lead follow-up automation")
duration = st.select_slider("3. Target duration", options=[15, 30, 45, 60], value=30)
language = st.selectbox("4. Script language", ["Hindi", "Hinglish"])
script = st.text_area("5. Script (optional — generated from topic if blank)", height=160,
                      placeholder="Enter or edit the words you want spoken.")
voice = st.radio("6. Voiceover", ["Generate Hindi voice (internet required)", "Upload recorded voiceover"])
audio_upload = st.file_uploader("Upload voiceover (up to 30 MB)", type=["mp3", "wav", "m4a"]) if voice.startswith("Upload") else None
music = st.file_uploader("7. Optional background music (up to 15 MB)", type=["mp3", "wav", "m4a"])

if st.button("Generate Reel", type="primary", use_container_width=True):
    if photo is None:
        st.error("Please upload a photo first.")
        st.stop()
    if len(photo.getvalue()) > MAX_PHOTO_BYTES:
        st.error("Photo is too large. Please use a file under 10 MB.")
        st.stop()
    if not topic.strip() and not script.strip():
        st.error("Enter a topic or a script.")
        st.stop()
    if voice.startswith("Upload") and audio_upload is None:
        st.error("Please upload a recorded voiceover.")
        st.stop()
    if audio_upload is not None and len(audio_upload.getvalue()) > MAX_AUDIO_BYTES:
        st.error("Voiceover is too large. Please use a file under 30 MB.")
        st.stop()
    if music is not None and len(music.getvalue()) > MAX_MUSIC_BYTES:
        st.error("Background music is too large. Please use a file under 15 MB.")
        st.stop()

    work = Path(tempfile.mkdtemp(prefix="kiran_reel_"))
    try:
        with st.spinner("Creating your Reel. Keep this page open until it finishes…"):
            img = work / "photo.png"
            img.write_bytes(photo.getvalue())
            validate_image(img)

            final_script = script.strip() or make_script(topic, duration, language)
            if not final_script.strip():
                raise ValueError("Could not create a script. Please enter one manually.")
            subtitle_file = work / "captions.srt"
            srt_content = make_srt(final_script, duration)
            subtitle_file.write_text(srt_content, encoding="utf-8")

            audio = work / "voice.mp3"
            if voice.startswith("Upload"):
                audio.write_bytes(audio_upload.getvalue())
            else:
                make_audio(final_script, audio)
            if not audio.exists() or audio.stat().st_size == 0:
                raise ValueError("Voiceover generation returned an empty audio file.")

            music_path = None
            if music is not None:
                suffix = Path(music.name).suffix.lower()
                if suffix not in {".mp3", ".wav", ".m4a"}:
                    raise ValueError("Unsupported music format.")
                music_path = work / ("music" + suffix)
                music_path.write_bytes(music.getvalue())

            output = work / "kiran_talking_reel.mp4"
            render(img, audio, output, duration, subtitle_file, music_path)
            if not output.exists() or output.stat().st_size == 0:
                raise ValueError("Video rendering finished without a usable MP4.")
            video_bytes = output.read_bytes()
            info = ffprobe_info(output)

        st.success("Reel created. Preview it and review the audio before publishing.")
        st.video(video_bytes)
        st.download_button("Download MP4", video_bytes, "kiran_talking_reel.mp4", "video/mp4", use_container_width=True)
        caption = make_caption(topic or "AI workflow", final_script)
        st.subheader("Your script")
        st.text_area("Review script", final_script, height=160)
        st.download_button("Download script", final_script, "hindi_script.txt", "text/plain")
        st.subheader("Instagram caption")
        st.text_area("Review caption", caption, height=140)
        st.download_button("Download caption", caption, "caption.txt", "text/plain")
        st.download_button("Download subtitles (SRT)", srt_content, "captions.srt", "application/x-subrip")
        with st.expander("Technical video details"):
            st.json(info)
        st.warning("Before posting, check pronunciation, subtitle timing, face framing, music rights, and video quality. This is a narrated-photo effect, not realistic lip-sync.")
    except Exception as exc:
        st.error(f"Reel creation failed: {exc}")
        st.info("Try a smaller photo/audio file, upload your own voiceover, or retry once. If it keeps failing, share the full error message.")
    finally:
        shutil.rmtree(work, ignore_errors=True)
