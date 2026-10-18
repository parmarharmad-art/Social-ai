#!/usr/bin/env python3
"""Publish a publicly reachable MP4 as an Instagram Reel via Instagram Graph API.

Required environment:
  INSTAGRAM_USER_ID
  INSTAGRAM_ACCESS_TOKEN
  INSTAGRAM_REEL_VIDEO_URL  (public HTTPS URL; GitHub raw URLs are not recommended)
Optional:
  INSTAGRAM_CAPTION
  META_GRAPH_API_VERSION (defaults to v22.0; set to a version supported by your Meta app)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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

def main():
    user_id = os.getenv("INSTAGRAM_USER_ID", "").strip()
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
    video_url = os.getenv("INSTAGRAM_REEL_VIDEO_URL", "").strip()
    caption = os.getenv("INSTAGRAM_CAPTION", "Created with SocialPilot AI").strip()
    missing = [name for name, value in [
        ("INSTAGRAM_USER_ID", user_id),
        ("INSTAGRAM_ACCESS_TOKEN", token),
        ("INSTAGRAM_REEL_VIDEO_URL", video_url),
    ] if not value]
    if missing:
        print("Instagram publishing skipped; missing configuration: " + ", ".join(missing))
        sys.exit(2)
    if not video_url.startswith("https://"):
        raise RuntimeError("INSTAGRAM_REEL_VIDEO_URL must be a public HTTPS URL.")
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
