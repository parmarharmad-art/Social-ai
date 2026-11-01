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
                headers={"User-Agent": "KiranBookReels/1.1 (book-summary-video-builder)"}
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

def norm(value):
    return "".join(ch for ch in value.casefold() if ch.isalnum())

def find_cover(row):
    wanted_title = row["book"].strip()
    wanted_norm = norm(wanted_title)
    wanted_authors = [part.strip().casefold() for part in row["author"].replace(" and ", ",").split(",") if part.strip()]
    queries = [wanted_title, wanted_title.replace("The ", "", 1), wanted_title + " " + row["author"]]
    seen = set()
    docs = []
    for query in queries:
        if query.casefold() in seen:
            continue
        seen.add(query.casefold())
        params = urllib.parse.urlencode({
            "title": query,
            "limit": 100,
            "fields": "title,author_name,cover_i"
        })
        payload = json.loads(get("https://openlibrary.org/search.json?" + params).decode("utf-8"))
        docs.extend(payload.get("docs", []))
        time.sleep(0.4)

    # Prefer title + author matches. Open Library sometimes indexes co-authors
    # separately or appends subtitles to the displayed title.
    unique = {}
    for doc in docs:
        if doc.get("cover_i"):
            key = (doc.get("key"), doc.get("cover_i"))
            unique[key] = doc
    docs = list(unique.values())

    def author_match(doc):
        authors = " ".join(doc.get("author_name", [])).casefold()
        return any(name.split()[-1] in authors for name in wanted_authors)

    def title_match(doc):
        title_norm = norm(str(doc.get("title", "")))
        return bool(wanted_norm and (wanted_norm in title_norm or title_norm in wanted_norm))

    for doc in docs:
        if title_match(doc) and author_match(doc):
            return doc["cover_i"]
    # Author metadata is sometimes absent, but only accept a title match
    # that includes the complete normalized requested title.
    for doc in docs:
        title_norm = norm(str(doc.get("title", "")))
        if doc.get("cover_i") and wanted_norm and wanted_norm in title_norm:
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
        time.sleep(0.5)
    if len(list(out.glob("book_*.png"))) != len(rows):
        raise SystemExit("Book-cover count mismatch")
if __name__ == "__main__":
    main()
