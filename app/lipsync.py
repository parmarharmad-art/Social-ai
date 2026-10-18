"""Photo-only Hindi voice and MuseTalk lip-sync workflow using a free public GPU Space."""
import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

import edge_tts
import imageio_ffmpeg
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response

router = APIRouter()
log = logging.getLogger(__name__)
SPACE = "https://henrybit-musetalk-1-5.hf.space"
MAX_PHOTO_BYTES = 10 * 1024 * 1024

# Short, ready-to-speak Hindi scripts. The script is selected automatically;
# no voice recording or audio upload is required from the user.
SCRIPTS = [
    "AI se apna content smart banaiye. Aise tips ke liye follow karein.",
    "Repetitive kaam automate karein, samay bachayein. AI tips ke liye follow karein.",
    "AI tools se daily workflow aasan banayein. Aur tips ke liye follow karein.",
    "Coding ke bina bhi AI automation shuru karein. Follow for practical tips.",
]


@router.get("/lipsync", response_class=HTMLResponse)
async def lipsync_workspace():
    return HTMLResponse(r"""<!doctype html>
<html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>Photo to Hindi Reel | SocialPilot AI</title>
<style>
:root{color-scheme:dark;--bg:#08111f;--panel:#111d30;--text:#eef5ff;--muted:#b6c5d9;--accent:#43d9ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,sans-serif}
main{max-width:700px;margin:auto;padding:20px}h1{font-size:clamp(1.8rem,6vw,2.5rem);line-height:1.15}
.panel{background:var(--panel);border:1px solid #263954;border-radius:16px;padding:18px;margin:16px 0}
p,small{color:var(--muted)}input,button{width:100%;padding:14px;border-radius:10px;margin:8px 0;font:inherit}
input{background:#08111f;border:1px solid #38506e;color:var(--text)}button{border:0;background:var(--accent);color:#06111b;font-weight:800}
button:disabled{opacity:.55}video{width:100%;margin-top:12px;border-radius:12px}a{color:var(--accent)}
#status{white-space:pre-wrap}.hide{display:none}
</style></head><body><main>
<p>SocialPilot AI · Kiran Kumar • AI Automation</p>
<h1>Photo se Hindi Talking Reel</h1>
<p>Sirf photo upload karein. Hindi script, Hindi voice aur lip-sync video automatically banane ki koshish hogi.</p>
<section class="panel">
<label for="photo"><strong>Apni clear, front-facing photo select karein</strong></label>
<input id="photo" type="file" accept="image/jpeg,image/png,image/webp" required>
<button id="go">Generate Hindi Reel</button>
<p id="status" role="status">Photo select karke Generate dabayein. Free GPU par queue ho sakti hai.</p>
</section>
<section id="result" class="panel hide"><h2>Generated Reel</h2><p id="script"></p><video id="video" controls playsinline></video><a id="download" download="hindi-lipsync-reel.mp4">Download MP4</a></section>
<p><small>Free shared GPU is used for lip-sync. Upload your photo only; the service creates the voice audio automatically. Do not close the page while it is generating.</small></p>
<p><a href="/">Back to SocialPilot AI</a></p>
</main>
<script>
const photo=document.getElementById('photo'),go=document.getElementById('go'),status=document.getElementById('status');
go.addEventListener('click',async()=>{
 if(!photo.files||!photo.files[0]){status.textContent='Pehle photo select karein.';return;}
 const f=photo.files[0];
 if(f.size>10*1024*1024){status.textContent='Photo 10 MB se chhoti honi chahiye.';return;}
 go.disabled=true;status.textContent='Step 1/3: Hindi voice generate ho rahi hai…';
 document.getElementById('result').classList.add('hide');
 try{
  const fd=new FormData();fd.append('photo',f);
  status.textContent='Step 1/3: Hindi voice aur script taiyar ho rahi hai. Ismein thoda samay lag sakta hai…';
  const res=await fetch('/api/lipsync/generate',{method:'POST',body:fd});
  if(!res.ok){let msg='Generation failed.';try{const j=await res.json();msg=j.detail||msg;}catch{}throw new Error(msg);}
  status.textContent='Step 2/3: Lip-sync video ready ho raha hai…';
  const blob=await res.blob();const url=URL.createObjectURL(blob);
  document.getElementById('video').src=url;const dl=document.getElementById('download');dl.href=url;
  const sc=res.headers.get('X-Generated-Script');document.getElementById('script').textContent=sc?'Hindi script: '+decodeURIComponent(sc):'Hindi voice generated.';
  document.getElementById('result').classList.remove('hide');status.textContent='Done — MP4 generate ho gaya. Video play karein ya download karein.';
 }catch(e){status.textContent='Error: '+(e.message||'Generation failed')+'\nAgar free GPU busy hai to kuch der baad dobara try karein.';}
 finally{go.disabled=false;}
});
</script></body></html>""")


async def _upload_to_space(client: httpx.AsyncClient, name: str, payload: bytes, mime: str) -> str:
    response = await client.post(
        f"{SPACE}/gradio_api/upload",
        files=[("files", (name, payload, mime))],
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Free lip-sync server rejected an input file. Retry in a few minutes.")
    data = response.json()
    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=502, detail="Free lip-sync server returned an invalid upload response.")
    return data[0]


async def _run_musetalk(client: httpx.AsyncClient, audio_path: str, photo_path: str) -> dict:
    payload = {
        "data": [
            {"path": audio_path, "meta": {"_type": "gradio.FileData"}},
            {"path": photo_path, "meta": {"_type": "gradio.FileData"}},
            0,
            10,
            "jaw",
            90,
            90,
        ]
    }
    response = await client.post(f"{SPACE}/gradio_api/call/generate", json=payload, timeout=45)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Free GPU model could not start the job. Retry later.")
    event_id = response.json().get("event_id")
    if not event_id:
        raise HTTPException(status_code=502, detail="Lip-sync server did not return a job ID.")
    try:
        async with client.stream("GET", f"{SPACE}/gradio_api/call/generate/{event_id}", timeout=360) as stream:
            event = ""
            async for line in stream.aiter_lines():
                if line.startswith("event:"):
                    event = line.partition(":")[2].strip()
                elif line.startswith("data:") and event in ("complete", "error"):
                    data = line.partition(":")[2].strip()
                    if event == "error":
                        log.error("MuseTalk Space generation error: %s", data[:1200])
                        try:
                            error_info = json.loads(data)
                            error_text = str(error_info.get("error") or error_info.get("message") or data)
                        except Exception:
                            error_text = data
                        raise HTTPException(status_code=502, detail="MuseTalk model error: " + error_text[:500])
                    result = json.loads(data)
                    if not isinstance(result, list) or not result or not isinstance(result[0], dict):
                        raise HTTPException(status_code=502, detail="Lip-sync model returned no video.")
                    video = result[0].get("video") or {}
                    video_url = video.get("url")
                    if not video_url and video.get("path"):
                        video_url = f"{SPACE}/gradio_api/file={quote(video['path'], safe='/')}"
                    if not video_url:
                        raise HTTPException(status_code=502, detail="Lip-sync model finished without an MP4 link.")
                    file_response = await client.get(video_url, timeout=120)
                    if file_response.status_code >= 400 or not file_response.content[:4] in (b"\x00\x00\x00\x18", b"\x00\x00\x00\x20", b"\x00\x00\x00\x1c", b"\x00\x00\x00\x1c"):
                        # MP4's ftyp box is usually at byte offset 4; validate below too.
                        if len(file_response.content) < 12 or file_response.content[4:8] != b"ftyp":
                            raise HTTPException(status_code=502, detail="Lip-sync result could not be downloaded as a valid MP4.")
                    if len(file_response.content) < 1000 or file_response.content[4:8] != b"ftyp":
                        raise HTTPException(status_code=502, detail="Lip-sync result is empty or not a valid MP4.")
                    return {"bytes": file_response.content, "note": result[1] if len(result) > 1 else ""}
        raise HTTPException(status_code=504, detail="Lip-sync timed out before the free GPU returned a video. Retry later.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Free GPU took too long. Retry later; no video was returned.")


@router.post("/api/lipsync/generate")
async def generate_photo_only_reel(photo: UploadFile = File(...)):
    if photo.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG or WEBP photo.")
    photo_bytes = await photo.read(MAX_PHOTO_BYTES + 1)
    if not photo_bytes or len(photo_bytes) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="Photo must be between 1 byte and 10 MB.")
    if photo.content_type == "image/jpeg" and not photo_bytes.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=400, detail="This does not look like a valid JPEG photo.")
    if photo.content_type == "image/png" and not photo_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="This does not look like a valid PNG photo.")
    if photo.content_type == "image/webp" and not (photo_bytes.startswith(b"RIFF") and photo_bytes[8:12] == b"WEBP"):
        raise HTTPException(status_code=400, detail="This does not look like a valid WEBP photo.")

    # Choose a compact Hindi script by day; the user only needs to provide the photo.
    import datetime
    script = SCRIPTS[datetime.date.today().toordinal() % len(SCRIPTS)]
    with tempfile.TemporaryDirectory(prefix="socialpilot_lipsync_") as tmp:
        audio_file = str(Path(tmp) / "hindi_voice.mp3")
        wav_file = str(Path(tmp) / "hindi_voice.wav")
        try:
            await edge_tts.Communicate(script, voice="hi-IN-SwaraNeural", rate="-5%").save(audio_file)
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            conversion = subprocess.run(
                [ffmpeg, "-y", "-i", audio_file, "-vn", "-ac", "1", "-ar", "16000", wav_file],
                capture_output=True, text=True, timeout=30,
            )
            if conversion.returncode != 0 or not Path(wav_file).exists():
                log.error("Hindi audio WAV conversion failed: %s", conversion.stderr[-1000:])
                raise RuntimeError("Could not convert generated Hindi voice to WAV.")
        except Exception:
            log.exception("Hindi TTS generation or WAV conversion failed")
            raise HTTPException(status_code=502, detail="Hindi voice generation failed. Please retry.")
        audio_bytes = Path(wav_file).read_bytes()
        if len(audio_bytes) < 1000 or audio_bytes[:4] != b"RIFF":
            raise HTTPException(status_code=502, detail="Hindi voice generator returned invalid audio.")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(360, connect=25)) as client:
                audio_path = await _upload_to_space(client, "hindi_voice.wav", audio_bytes, "audio/wav")
                photo_path = await _upload_to_space(client, photo.filename or "photo.jpg", photo_bytes, photo.content_type)
                output = await _run_musetalk(client, audio_path, photo_path)
        except HTTPException:
            raise
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Free lip-sync server timed out. Retry later.")
        except Exception:
            log.exception("Photo-to-Hindi-lip-sync job failed")
            raise HTTPException(status_code=502, detail="Photo-to-video generation failed. Retry later.")
    from urllib.parse import quote as quote_header
    return Response(
        content=output["bytes"],
        media_type="video/mp4",
        headers={
            "Content-Disposition": 'attachment; filename="hindi-lipsync-reel.mp4"',
            "X-Generated-Script": quote_header(script, safe=""),
            "Cache-Control": "no-store",
        },
    )
