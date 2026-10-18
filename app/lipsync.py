"""Mobile-first launcher for the free MuseTalk lip-sync demo.

Inference is performed by the public Hugging Face Space; this Render service
does not run GPU inference. Use a top-level navigation instead of an embedded
iframe because embedded Gradio uploads can fail in mobile in-app browsers.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/lipsync", response_class=HTMLResponse)
async def lipsync_workspace():
    return HTMLResponse("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Free Hindi Lip-Sync Studio — SocialPilot AI</title>
<style>
:root{color-scheme:dark;--bg:#08111f;--panel:#111d30;--text:#eef5ff;--muted:#b6c5d9;--accent:#43d9ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:760px;margin:auto;padding:20px}h1{font-size:clamp(1.7rem,5vw,2.5rem);line-height:1.15;margin:.5rem 0 1rem}
p,li{color:var(--muted)}.panel{background:var(--panel);border:1px solid #263954;border-radius:16px;padding:18px;margin:16px 0}
a.btn{display:block;text-align:center;background:var(--accent);color:#06111b;font-weight:800;text-decoration:none;padding:15px 16px;border-radius:12px;margin:12px 0}
a.secondary{background:#1c2b43;color:var(--text);border:1px solid #38506e}
.small{font-size:.9rem}.warning{border-left:4px solid #f6c453;padding-left:12px}
</style></head><body><main>
<p>SocialPilot AI · Kiran Kumar • AI Automation</p>
<h1>Free Photo-to-Hindi-Speech Lip-Sync</h1>
<p><strong>Important fix:</strong> open the generator directly. The embedded model frame has been removed to avoid upload/JavaScript errors in mobile in-app browsers.</p>
<div class="panel">
<h2>Start generating</h2>
<p>Open the full-screen MuseTalk generator, then upload your Hindi voiceover in <strong>Driving Audio</strong> and your face photo in <strong>Reference Image or Video</strong>. Press <strong>2. Generate</strong> and wait for the output video.</p>
<a class="btn" href="https://henrybit-musetalk-1-5.hf.space/" target="_blank" rel="noopener noreferrer">Open MuseTalk Generator (Full Screen)</a>
<a class="btn secondary" href="https://huggingface.co/spaces/henrybit/musetalk-1-5" target="_blank" rel="noopener noreferrer">Open Model Page / Space Status</a>
</div>
<div class="panel">
<h2>Before you generate</h2>
<ol><li>Use a clear, front-facing photo with the full face visible.</li><li>Use a short Hindi voiceover first for testing.</li><li>If the demo shows a queue, wait for its turn. If it shows a model/runtime error, retry later; free GPU availability is not guaranteed.</li><li>Download the resulting MP4 only after it appears in the output video area.</li></ol>
</div>
<div class="panel warning"><strong>Free-tier note:</strong> MuseTalk runs on an external shared GPU service. This page cannot force its GPU allocation or guarantee the external service will complete a job. Your photo/audio are uploaded to that service for processing.</div>
<p class="small">No video is marked successful unless the generator returns an MP4.</p>
</main></body></html>""")
