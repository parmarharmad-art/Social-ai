#!/usr/bin/env python3
"""Fetch a matching book-cover thumbnail for each book using Google Books."""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

def get(url, attempts=5):
    import time
    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SocialAI-BookReels/1.0"})
            with urllib.request.urlopen(req, timeout=35) as response:
                return response.read()
        except Exception as exc:
            last = exc
            delay = min(60, 5 * (2 ** attempt))
            print("Request failed; retrying in", delay, "seconds:", exc, flush=True)
            time.sleep(delay)
    raise RuntimeError("Book cover request failed after retries: " + str(last))

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: prepare_book_covers.py book_summaries.json output_dir")
    rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for row in rows:
        query = urllib.parse.urlencode({"q": "intitle:" + row["book"] + " inauthor:" + row["author"], "maxResults": 5})
        payload = json.loads(get("https://www.googleapis.com/books/v1/volumes?" + query).decode("utf-8"))
        cover = None
        for item in payload.get("items", []):
            links = item.get("volumeInfo", {}).get("imageLinks", {})
            cover = links.get("thumbnail") or links.get("smallThumbnail")
            if cover:
                break
        if not cover:
            raise SystemExit("No matching book-cover image found for: " + row["book"])
        data = get(cover.replace("http://", "https://").replace("&edge=curl", ""))
        if len(data) < 3000:
            raise SystemExit("Book-cover image is too small: " + row["book"])
        path = out / ("book_%02d.png" % int(row["id"]))
        path.write_bytes(data)
        print("Fetched cover:", row["book"], "->", path.name, len(data), "bytes")
        time.sleep(3)
    if len(list(out.glob("book_*"))) != len(rows):
        raise SystemExit("Book-cover count mismatch")

if __name__ == "__main__":
    main()
