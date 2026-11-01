#!/usr/bin/env python3
"""Publish the newest generated MP4 as an Instagram Reel.

Required GitHub Actions secrets:
  INSTAGRAM_USER_ID
  INSTAGRAM_ACCESS_TOKEN
Optional workflow inputs / repository variables:
  reel_number (latest or an exact numbered MP4 such as 07)
  caption (overrides the matching reels.json caption)
  INSTAGRAM_REEL_VIDEO_URL (overrides the auto-selected public GitHub raw URL)
  META_GRAPH_API_VERSION
The repository must be public for the default raw URL to be fetchable by Meta.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v22.0")
BASE = f"https://graph.instagram.com/{API_VERSION}"

def request(method, url, data=None):
    payload = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=payload, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            if response.status >= 400:
                raise RuntimeError(f"Meta API HTTP {response.status}: {body}")
            return parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Meta API HTTP {exc.code}: {body}") from exc

def select_reel():
    reel_dir = Path("social-content/reels")
    requested = os.getenv("INSTAGRAM_REEL_NUMBER", "latest").strip().lower()
    candidates = {p.stem: p for p in reel_dir.glob("*.mp4") if p.is_file() and p.stem.isdigit()}
    if not candidates:
        raise RuntimeError("No generated numbered MP4 found in social-content/reels.")
    if requested in ("", "latest"):
        key = max(candidates, key=lambda value: int(value))
    else:
        key = str(int(requested)).zfill(2)
        if key not in candidates:
            raise RuntimeError(f"Requested Reel {requested} was not generated. Available: {', '.join(sorted(candidates))}")
    return int(key), candidates[key]


def resolve_video_url(path):
    override = os.getenv("INSTAGRAM_REEL_VIDEO_URL", "").strip()
    if override:
        if not override.startswith("https://"):
            raise RuntimeError("INSTAGRAM_REEL_VIDEO_URL must be a public HTTPS URL.")
        return override
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    if not repo:
        raise RuntimeError("No INSTAGRAM_REEL_VIDEO_URL and GITHUB_REPOSITORY is unavailable.")
    # The workflow commits/pushes outputs before this step; repository must be public.
    return f"https://raw.githubusercontent.com/{repo}/main/{path.as_posix()}"


def resolve_caption(reel_number):
    override = os.getenv("INSTAGRAM_CAPTION", "").strip()
    if override:
        return override
    content_file = Path("social-content/reels.json")
    if content_file.exists():
        with content_file.open(encoding="utf-8") as handle:
            items = json.load(handle)
        for item in items:
            if int(item.get("n", -1)) == reel_number:
                return str(item.get("cap", "Follow @officialkiraankumar for AI automation tips.")).strip()
    return "Follow @officialkiraankumar for AI automation tips."

def main():
    user_id = os.getenv("INSTAGRAM_USER_ID", "").strip()
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
    reel_number, reel_path = select_reel()
    caption = resolve_caption(reel_number)
    missing = [name for name, value in [
        ("INSTAGRAM_USER_ID", user_id),
        ("INSTAGRAM_ACCESS_TOKEN", token),
    ] if not value]
    if missing:
        print("Instagram publishing skipped; missing GitHub Actions secrets: " + ", ".join(missing))
        sys.exit(2)
    video_url = resolve_video_url(reel_path)
    print(f"Publishing Reel {reel_number:02d}: {video_url}")
    create = request("POST", f"{BASE}/{urllib.parse.quote(user_id)}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": token,
    })
    creation_id = create.get("id")
    if not creation_id:
        raise RuntimeError("Meta API did not return a container id: " + json.dumps(create))
    print(f"Created Reel container: {creation_id}")
    deadline = time.time() + 900
    while time.time() < deadline:
        status = request("GET", f"{BASE}/{urllib.parse.quote(creation_id)}?" + urllib.parse.urlencode({
            "fields": "status_code,status",
            "access_token": token,
        }))
        code = status.get("status_code")
        print("Reel processing status:", code or status.get("status") or "unknown")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError("Instagram Reel processing failed: " + json.dumps(status))
        time.sleep(10)
    else:
        raise TimeoutError("Instagram Reel container did not finish within 15 minutes.")
    published = request("POST", f"{BASE}/{urllib.parse.quote(user_id)}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    media_id = published.get("id")
    if not media_id:
        raise RuntimeError("Meta API did not confirm publish: " + json.dumps(published))
    print("INSTAGRAM_PUBLISH_SUCCESS media_id=" + media_id)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"::error::{exc}")
        sys.exit(1)
