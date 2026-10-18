"""Free, open-source MuseTalk lip-sync workspace link.

The actual inference runs in a public Hugging Face ZeroGPU Space, not on this
Render web service. This avoids pretending Render's CPU-only free instance can
run GPU inference. If the public Space is busy or its free quota is exhausted,
open it directly and retry when capacity returns.
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
<title>Free AI Lip-Sync Studio — SocialPilot AI</title>
<style>
:root{color-scheme:dark;--bg:#08111f;--panel:#111d30;--text:#eef5ff;--muted:#a9bbd3;--accent:#43d9ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:auto;padding:20px}h1{font-size:clamp(1.6rem,4vw,2.5rem);line-height:1.15;margin:.4rem 0 1rem}
p{color:var(--muted)}.panel{background:var(--panel);border:1px solid #263954;border-radius:16px;padding:18px;margin:16px 0}
a.btn{display:inline-block;background:var(--accent);color:#06111b;font-weight:750;text-decoration:none;padding:12px 16px;border-radius:10px;margin:8px 8px 8px 0}
iframe{width:100%;height:78vh;min-height:620px;border:0;border-radius:12px;background:#fff}
.small{font-size:.9rem}.warning{border-left:4px solid #f6c453;padding-left:12px}
</style></head><body><main>
<p>SocialPilot AI · Kiran Kumar • AI Automation</p>
<h1>Free AI Photo-to-Speech Lip-Sync Studio</h1>
<p>Use the open-source MuseTalk 1.5 model through a public Hugging Face ZeroGPU demo. Upload a clear, front-facing photo and your Hindi voiceover, then generate a talking video.</p>
<div class="panel">
<strong>How to get the best result</strong>
<ol><li>Upload a clear, front-facing image with the full face visible.</li><li>Upload your Hindi voiceover audio (WAV/MP3 if supported by the demo).</li><li>Generate the video and preview the mouth movement before saving the MP4.</li><li>Use the finished MP4 in your Make.com Instagram publishing scenario.</li></ol>
<a class="btn" href="https://huggingface.co/spaces/henrybit/musetalk-1-5" target="_blank" rel="noopener">Open Lip-Sync Studio</a>
<a class="btn" href="https://huggingface.co/spaces/henrybit/musetalk-1-5" target="_blank" rel="noopener">Retry / Open Full Screen</a>
<p class="small">The live demo is hosted externally. Its free ZeroGPU capacity can queue, sleep, or temporarily become unavailable; this page does not claim a video is generated until the demo returns one.</p>
</div>
<div class="panel">
<h2>Live generator</h2>
<iframe src="https://henrybit-musetalk-1-5.hf.space" title="MuseTalk 1.5 lip-sync generator" loading="lazy" allow="clipboard-read; clipboard-write; microphone"></iframe>
</div>
<div class="panel warning">
<strong>Privacy:</strong> the photo and audio are uploaded to the external Hugging Face Space for processing. Only upload media you have permission to use. If the embedded interface does not load on your phone, use “Open Lip-Sync Studio” above.
</div>
</main></body></html>""")
