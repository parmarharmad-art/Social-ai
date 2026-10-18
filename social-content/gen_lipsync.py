#!/usr/bin/env python3
"""Generate true talking-photo Reels through HeyGen Avatar IV.
Requires HEYGEN_API_KEY. Output is saved separately from the branded infographic MP4s.
"""
import json, os, sys, time
from pathlib import Path
import requests

API = "https://api.heygen.com"
KEY = os.environ.get("HEYGEN_API_KEY", "").strip()
VOICE_ID = os.environ.get("HEYGEN_VOICE_ID", "9e02bd3d74bb48a6bbfe468177e1857b")
BASE = Path(__file__).resolve().parent
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "reels.json"
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else BASE / "reels_lipsync"
OUT.mkdir(parents=True, exist_ok=True)
HEADERS = {"X-Api-Key": KEY, "Content-Type": "application/json", "Accept": "application/json"}

def api(method, path, **kwargs):
    r = requests.request(method, API + path, headers=HEADERS, timeout=90, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"HeyGen API {r.status_code}: {r.text[:1200]}")
    return r.json()

def script_for(item):
    bits = [str(item.get("h", "")).strip()]
    bits += [str(p).strip() for p in item.get("pts", []) if str(p).strip()]
    bits.append(str(item.get("voice_cta", "AI automation ki practical tips ke liye Kiran Kumar ko follow karein.")).strip())
    return " ".join(x for x in bits if x)

def main():
    if not KEY:
        print("LIPSYNC_SKIPPED: HEYGEN_API_KEY is not configured; no fake/static lip-sync output was created.")
        return 0
    items = json.loads(DATA.read_text(encoding="utf-8"))
    manifest = []
    for item in items:
        n = int(item["n"])
        target = OUT / f"{n:02d}.mp4"
        if target.exists() and os.environ.get("SKIP_EXISTING_LIPSYNC") == "1":
            manifest.append({"n": n, "status": "existing", "file": target.name})
            continue
        photo = "person_rgba.png" if n % 2 else "person_b.png"
        photo_url = f"https://raw.githubusercontent.com/parmarharmad-art/Social-ai/main/social-content/assets/{photo}"
        payload = {
            "image_url": photo_url, "script": script_for(item), "voice_id": VOICE_ID,
            "title": f"Kiran Kumar AI Automation Reel {n:02d} — Hindi Lip Sync",
            "resolution": "720p", "aspect_ratio": "9:16",
            "voice_settings": {"speed": 1.03, "pitch": 2, "locale": "hi-IN"},
            "motion_prompt": "Natural young adult Indian male presenter, subtle head movement, friendly confident expression, realistic speech mouth movement synchronized to Hindi narration. Preserve identity.",
            "expressiveness": "high"
        }
        created = api("POST", "/v3/videos", json=payload)
        video_id = created.get("data", created).get("video_id")
        if not video_id:
            raise RuntimeError(f"HeyGen response has no video_id: {created}")
        print(f"Submitted lip-sync Reel {n:02d}: {video_id}", flush=True)
        deadline, video_url, status = time.time() + 1800, None, "pending"
        while time.time() < deadline:
            time.sleep(20)
            state = api("GET", f"/v3/videos/{video_id}").get("data", {})
            status = state.get("status", "unknown")
            print(f"Reel {n:02d} status: {status}", flush=True)
            if status == "completed":
                video_url = state.get("video_url")
                break
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"Lip-sync failed for Reel {n:02d}: {state}")
        if not video_url:
            raise TimeoutError(f"Lip-sync timed out for Reel {n:02d}; last status={status}")
        with requests.get(video_url, stream=True, timeout=180) as r:
            r.raise_for_status()
            with target.open("wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk: f.write(chunk)
        if target.stat().st_size < 100_000:
            target.unlink(missing_ok=True)
            raise RuntimeError(f"Downloaded MP4 too small for Reel {n:02d}")
        manifest.append({"n": n, "status": "completed", "file": target.name, "video_id": video_id})
        print(f"Verified talking-photo MP4 {target} ({target.stat().st_size} bytes)", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Completed {sum(x['status'] == 'completed' for x in manifest)} lip-sync Reels.", flush=True)
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as e:
        print(f"LIPSYNC_ERROR: {e}", file=sys.stderr, flush=True)
        raise
