#!/usr/bin/env python3
"""Fetch verified title/author book-cover images from Open Library."""
import json
from io import BytesIO
from PIL import Image
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

def get(url, attempts=4):
    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "KiranBookReels/1.0 (book-summary-video-builder)"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                delay = 4 * (attempt + 1)
                print("Request failed; retrying in", delay, "seconds:", exc, flush=True)
                time.sleep(delay)
    raise RuntimeError("Open Library request failed after retries: " + str(last))

def find_cover(row):
    params = urllib.parse.urlencode({
        "title": row["book"],
        "author": row["author"],
        "limit": 10,
        "fields": "title,author_name,cover_i"
    })
    payload = json.loads(get("https://openlibrary.org/search.json?" + params).decode("utf-8"))
    wanted_title = row["book"].strip().casefold()
    wanted_author = row["author"].strip().casefold()
    docs = payload.get("docs", [])
    # Prefer exact title + author; otherwise accept a result only when both
    # requested title and author are present in the returned metadata.
    for doc in docs:
        title = str(doc.get("title", "")).casefold()
        authors = " ".join(doc.get("author_name", [])).casefold()
        if doc.get("cover_i") and wanted_title in title and wanted_author in authors:
            return doc["cover_i"]
    for doc in docs:
        title = str(doc.get("title", "")).casefold()
        authors = " ".join(doc.get("author_name", [])).casefold()
        if doc.get("cover_i") and (wanted_title in title or title in wanted_title) and wanted_author in authors:
            return doc["cover_i"]
    return None

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: prepare_book_covers.py book_summaries.json output_dir")
    rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for row in rows:
        cover_id = find_cover(row)
        if not cover_id:
            raise SystemExit("No matching Open Library cover found for: " + row["book"] + " — " + row["author"])
        url = "https://covers.openlibrary.org/b/id/%s-L.jpg?default=false" % cover_id
        data = get(url)
        if len(data) < 3000 or not data.startswith(bytes.fromhex("ffd8ff")):
            raise SystemExit("Invalid or missing cover image for: " + row["book"])
        path = out / ("book_%02d.png" % int(row["id"]))
        with Image.open(BytesIO(data)) as cover:
            cover.convert("RGB").save(path, format="PNG", optimize=True)
        print("Fetched matching cover:", row["book"], "by", row["author"], "->", path.name, path.stat().st_size, "bytes", flush=True)
        time.sleep(1)
    if len(list(out.glob("book_*.png"))) != len(rows):
        raise SystemExit("Book-cover count mismatch")
if __name__ == "__main__":
    main()
