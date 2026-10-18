import html
import os
import shutil
import subprocess
import tempfile
import urllib.request
import uuid
from pathlib import Path

from flask import Flask, request, send_from_directory
from dotenv import load_dotenv

from src.hindi_tts import make_audio
from src.script_generator import make_caption, make_script
from src.subtitles import make_srt
from src.validation import ffprobe_info, validate_image
from src.video_renderer import render

load_dotenv()
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 55 * 1024 * 1024
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

PAGE = """<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kiran Kumar AI Reels Studio</title><style>
*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#f4f7ff;font:16px system-ui,sans-serif}
main{max-width:720px;margin:auto;padding:22px 15px 50px}.panel{background:#141d33;border:1px solid #2a3857;border-radius:18px;padding:20px;margin:16px 0}
h1{font-size:27px;margin:8px 0}p{color:#c5d0e8}.brand{color:#68d9ff;font-weight:700}
label{display:block;margin:16px 0 7px;font-weight:650}input,select,textarea{width:100%;padding:12px;border-radius:10px;border:1px solid #52617e;background:#0b1326;color:white;font:inherit}
textarea{min-height:120px}button,.download{display:block;width:100%;padding:15px;border:0;border-radius:12px;background:#1688ff;color:white;font-size:17px;font-weight:750;text-align:center;text-decoration:none;margin-top:20px}
small{color:#aebbd4}.error{background:#4b1c2a;padding:14px;border-radius:10px;color:#ffdbe2}.success{background:#123a32;padding:14px;border-radius:10px;color:#d5fff2}
video{width:100%;border-radius:12px;background:#000} .choice{display:flex;gap:8px;align-items:center}.choice input{width:auto}
</style></head><body><main><div class="brand">KIRAN KUMAR • AI AUTOMATION</div><h1>🎬 AI Reels Studio</h1><p>Create a vertical Hindi/Hinglish Reel with voiceover, subtitles and your brand watermark, with an optional free real lip-sync mode.</p>{content}</main></body></html>"""

def page(content):
    return PAGE.replace("{content}", content)

def media_duration(path):
    probe = shutil.which("ffprobe")
    if not probe:
        return None
    try:
        result = subprocess.run(
            [probe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return max(1.0, float(result.stdout.strip()))
    except Exception:
        app.logger.exception("Could not determine media duration")
    return None

def run_free_musetalk(audio_path, image_path, work_dir):
    """Call a public, no-token MuseTalk ZeroGPU Space. No paid API is used."""
    from gradio_client import Client

    app.logger.info("REEL_JOB lip_sync_submit space=henrybit/musetalk-1-5")
    client = Client("henrybit/musetalk-1-5", verbose=False)
    result = client.predict(
        str(audio_path), str(image_path), 0, 10, "jaw", 90, 90,
        api_name="/generate"
    )
    candidate = result[0] if isinstance(result, (tuple, list)) else result
    if isinstance(candidate, dict):
        candidate = candidate.get("path") or candidate.get("url") or candidate.get("video")
    if isinstance(candidate, dict):
        candidate = candidate.get("path") or candidate.get("url")
    if not candidate:
        raise RuntimeError("Free MuseTalk returned no video. Retry later or select photo-zoom mode.")
    candidate = str(candidate)
    target = Path(work_dir) / "musetalk_output.mp4"
    if candidate.startswith("https://") or candidate.startswith("http://"):
        urllib.request.urlretrieve(candidate, target)
    else:
        source = Path(candidate)
        if not source.exists() or source.stat().st_size < 1000:
            raise RuntimeError("Free MuseTalk did not return a downloadable MP4. Its public queue may be unavailable.")
        shutil.copy2(source, target)
    if not target.exists() or target.stat().st_size < 1000:
        raise RuntimeError("Free MuseTalk output failed the MP4 file check.")
    app.logger.info("REEL_JOB lip_sync_ready bytes=%s", target.stat().st_size)
    return target

@app.get("/")
def home():
    content = """
    <form class="panel" method="post" action="/generate" enctype="multipart/form-data">
      <label>1. Upload your photo (JPG, PNG or WEBP, max 10 MB)</label><input required type="file" name="photo" accept=".jpg,.jpeg,.png,.webp">
      <label>2. Reel topic</label><input name="topic" placeholder="WhatsApp lead follow-up automation">
      <label>3. Duration</label><select name="duration"><option>15</option><option selected>30</option><option>45</option><option>60</option></select>
      <label>4. Script language</label><select name="language"><option>Hindi</option><option>Hinglish</option></select>
      <label>5. Script (optional)</label><textarea name="script" placeholder="Leave blank to create a short script from the topic."></textarea>
      <label>6. Voiceover</label><select name="voice" id="voice" onchange="document.getElementById('audioRow').style.display=this.value==='upload'?'block':'none'"><option value="tts">Generate Hindi voice (internet required)</option><option value="upload">Upload recorded voiceover</option></select>
      <div id="audioRow" style="display:none"><label>Voiceover file (MP3, WAV, M4A; max 30 MB)</label><input type="file" name="audio" accept=".mp3,.wav,.m4a"></div>
      <label>7. Optional background music (MP3, WAV, M4A; max 15 MB)</label><input type="file" name="music" accept=".mp3,.wav,.m4a">
      <label>8. Talking-photo mode</label><select name="lip_sync"><option value="musetalk" selected>Real mouth lip-sync — free MuseTalk (may queue)</option><option value="photo">Photo zoom + narration (faster fallback)</option></select>
      <button id="generateBtn" type="submit">Generate My Reel</button><div id="busy" class="panel success" style="display:none"><b>Reel generation started…</b><p>Photo check → Hindi voiceover → video rendering → MP4 validation. Keep this page open; 30–60 second reels can take a few minutes.</p></div><p><small>Real lip-sync uses a public free MuseTalk ZeroGPU Space, so queue/quota availability can vary. Choose photo zoom mode if the free service is unavailable. Review your video before publishing.</small></p>
    </form><script>document.querySelector("form").addEventListener("submit",function(){document.getElementById("busy").style.display="block";const b=document.getElementById("generateBtn");b.disabled=true;b.textContent="Generating… keep page open";});</script>"""
    return page(content)

@app.post("/generate")
def generate():
    work = Path(tempfile.mkdtemp(prefix="kiran_reel_"))
    try:
        photo = request.files.get("photo")
        topic = request.form.get("topic", "").strip()
        script = request.form.get("script", "").strip()
        try:
            duration = int(request.form.get("duration", "30"))
        except ValueError:
            duration = 30
        if duration not in (15, 30, 45, 60):
            duration = 30
        language = request.form.get("language", "Hindi")
        voice = request.form.get("voice", "tts")
        lip_sync = request.form.get("lip_sync", "musetalk")
        if lip_sync not in ("musetalk", "photo"):
            lip_sync = "musetalk"
        audio_upload = request.files.get("audio")
        music = request.files.get("music")
        if not photo or not photo.filename:
            return page('<div class="panel error">Please upload a photo, then try again.</div><a class="download" href="/">Go back</a>'), 400
        if len(photo.read()) > 10 * 1024 * 1024:
            return page('<div class="panel error">Photo exceeds 10 MB. Choose a smaller image.</div><a class="download" href="/">Go back</a>'), 400
        photo.stream.seek(0)
        if not topic and not script:
            return page('<div class="panel error">Enter a topic or a script.</div><a class="download" href="/">Go back</a>'), 400
        if voice == "upload" and (not audio_upload or not audio_upload.filename):
            return page('<div class="panel error">Choose your voiceover file.</div><a class="download" href="/">Go back</a>'), 400
        if audio_upload and audio_upload.filename and len(audio_upload.read()) > 30 * 1024 * 1024:
            return page('<div class="panel error">Voiceover exceeds 30 MB.</div><a class="download" href="/">Go back</a>'), 400
        if audio_upload and audio_upload.filename:
            audio_upload.stream.seek(0)
        if music and music.filename and len(music.read()) > 15 * 1024 * 1024:
            return page('<div class="panel error">Music exceeds 15 MB.</div><a class="download" href="/">Go back</a>'), 400
        if music and music.filename:
            music.stream.seek(0)

        app.logger.info("REEL_JOB started duration=%s voice=%s", duration, voice)
        photo_ext = Path(photo.filename).suffix.lower()
        if photo_ext not in (".jpg", ".jpeg", ".png", ".webp"):
            return page('<div class="panel error">Use a JPG, PNG, or WEBP photo file.</div><a class="download" href="/">Go back</a>'), 400
        img = work / ("photo" + photo_ext)
        img.write_bytes(photo.read())
        validate_image(img)
        final_script = script or make_script(topic, duration, language)
        if not final_script.strip():
            raise ValueError("Script is empty. Enter your own script and retry.")
        audio = work / "voice.mp3"
        app.logger.info("REEL_JOB script_ready chars=%s", len(final_script))
        if voice == "upload":
            ext = Path(audio_upload.filename).suffix.lower()
            if ext not in (".mp3", ".wav", ".m4a"):
                raise ValueError("Voiceover must be MP3, WAV, or M4A.")
            audio = work / ("voice" + ext)
            audio.write_bytes(audio_upload.read())
        else:
            make_audio(final_script, audio)
        if not audio.exists() or audio.stat().st_size < 1000:
            raise ValueError("No usable voiceover was created.")
        music_path = None
        if music and music.filename:
            ext = Path(music.filename).suffix.lower()
            if ext not in (".mp3", ".wav", ".m4a"):
                raise ValueError("Music must be MP3, WAV, or M4A.")
            music_path = work / ("music" + ext)
            music_path.write_bytes(music.read())
        app.logger.info("REEL_JOB audio_ready bytes=%s", audio.stat().st_size)
        audio_duration = media_duration(audio)
        render_duration = max(1, min(60, round(audio_duration or duration)))
        subtitle_file = work / "captions.srt"
        subtitle_file.write_text(make_srt(final_script, render_duration), encoding="utf-8")
        talking_video = None
        if lip_sync == "musetalk":
            talking_video = run_free_musetalk(audio, img, work)
            render_duration = max(1, min(60, round(media_duration(talking_video) or audio_duration or duration)))
        job_id = uuid.uuid4().hex
        output = OUTPUT_DIR / (job_id + ".mp4")
        render(img, audio, output, render_duration, subtitle_file, music_path,
               talking_video_path=talking_video)
        app.logger.info("REEL_JOB render_done bytes=%s lip_sync=%s", output.stat().st_size if output.exists() else 0, lip_sync)
        info = ffprobe_info(output)
        app.logger.info("REEL_JOB validated job_id=%s", job_id)
        caption = make_caption(topic or "AI workflow", final_script)
        safe_script = html.escape(final_script)
        safe_caption = html.escape(caption)
        safe_info = html.escape(str(info))
        content = f"""
        <div class="panel success">Reel generated successfully. Preview it, then download the MP4.</div>
        <div class="panel"><video controls playsinline src="/output/{job_id}"></video><a class="download" href="/output/{job_id}?download=1">⬇ Download MP4 Reel</a></div>
        <div class="panel"><h2>Your script</h2><p>{safe_script}</p><a class="download" href="/text/{job_id}/script">Download script</a></div>
        <div class="panel"><h2>Instagram caption</h2><p>{safe_caption}</p><a class="download" href="/text/{job_id}/caption">Download caption</a></div>
        <div class="panel"><h2>Video details</h2><small>{safe_info}</small></div>
        <a class="download" href="/">Create another Reel</a>"""
        (OUTPUT_DIR / (job_id + ".txt")).write_text(final_script, encoding="utf-8")
        (OUTPUT_DIR / (job_id + "_caption.txt")).write_text(caption, encoding="utf-8")
        return page(content)
    except Exception as exc:
        app.logger.exception("REEL_JOB failed")
        message = html.escape(str(exc))
        return page(f'<div class="panel error"><b>Reel generation failed</b><p>{message}</p></div><a class="download" href="/">Try again</a>'), 500
    finally:
        shutil.rmtree(work, ignore_errors=True)

@app.get("/output/<job_id>")
def output_file(job_id):
    if not job_id.isalnum():
        return "Invalid file ID", 400
    path = OUTPUT_DIR / (job_id + ".mp4")
    if not path.exists():
        return "This Reel file is no longer available. Generate it again.", 404
    return send_from_directory(OUTPUT_DIR, path.name, as_attachment=request.args.get("download") == "1", mimetype="video/mp4", download_name="kiran_talking_reel.mp4")

@app.get("/text/<job_id>/<kind>")
def text_file(job_id, kind):
    if not job_id.isalnum() or kind not in ("script", "caption"):
        return "Invalid file", 400
    suffix = ".txt" if kind == "script" else "_caption.txt"
    path = OUTPUT_DIR / (job_id + suffix)
    if not path.exists():
        return "File no longer available", 404
    return send_from_directory(OUTPUT_DIR, path.name, as_attachment=True, download_name=kind + ".txt")

@app.errorhandler(413)
def too_large(_error):
    return page('<div class="panel error">Upload too large. Check the file-size limits and retry.</div><a class="download" href="/">Go back</a>'), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8501")))
