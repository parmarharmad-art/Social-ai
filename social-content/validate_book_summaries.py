#!/usr/bin/env python3
"""Strict structural and editorial-safety QA for the 30-day book-summary library."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "book_summaries.json"
REPORT = ROOT / "book-summary-quality-report.json"
EXPECTED_COUNT = 30
REQUIRED = {
    "id", "book", "author", "theme", "hook", "voiceover",
    "caption", "scenes", "cta", "hashtags",
}
TEXT_FIELDS = ("book", "author", "theme", "hook", "caption", "cta")
HASHTAG_RE = re.compile(r"^#[A-Za-z][A-Za-z0-9_]*$")
FACE_RE = re.compile(r"\b(face reveal|show face|talking head|on-camera presenter)\b", re.I)
COPY_RISK_RE = re.compile(r"\b(full chapter|entire chapter|full audiobook|download the pdf)\b", re.I)


def fail(message: str) -> None:
    raise ValueError(message)


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> None:
    if not DATA.is_file():
        fail(f"Missing source file: {DATA.name}")

    try:
        rows = json.loads(DATA.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")

    if not isinstance(rows, list):
        fail("Top-level JSON value must be an array")
    if len(rows) != EXPECTED_COUNT:
        fail(f"Expected exactly {EXPECTED_COUNT} packages; found {len(rows)}")

    ids: list[int] = []
    normalized_hooks: list[str] = []
    all_hashtags: Counter[str] = Counter()
    scene_count = 0
    voiceover_words = 0
    caption_chars = 0

    for index, row in enumerate(rows, start=1):
        label = f"Entry {index}"
        if not isinstance(row, dict):
            fail(f"{label}: must be a JSON object")

        missing = REQUIRED - set(row)
        if missing:
            fail(f"{label}: missing fields: {', '.join(sorted(missing))}")

        item_id = row["id"]
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 1:
            fail(f"{label}: id must be a positive integer")
        ids.append(item_id)

        for key in TEXT_FIELDS:
            if not nonempty_text(row[key]):
                fail(f"{label}: {key} must be a non-empty string")
            if row[key] != row[key].strip():
                fail(f"{label}: {key} has leading/trailing whitespace")

        hook_key = re.sub(r"[^a-z0-9]+", " ", row["hook"].lower()).strip()
        normalized_hooks.append(hook_key)
        if len(row["hook"].split()) < 5:
            fail(f"{label}: hook is too short to provide useful context")

        voiceover = row["voiceover"]
        if not isinstance(voiceover, list) or len(voiceover) != 3:
            fail(f"{label}: voiceover must contain exactly 3 beats")
        if not all(nonempty_text(beat) for beat in voiceover):
            fail(f"{label}: every voiceover beat must be non-empty text")
        voiceover_words += len(" ".join(voiceover).split())
        if len(" ".join(voiceover).split()) < 35:
            fail(f"{label}: voiceover is too short for a useful Reel script")

        scenes = row["scenes"]
        if not isinstance(scenes, list) or len(scenes) != 3:
            fail(f"{label}: expected exactly 3 faceless scenes")
        for scene_index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                fail(f"{label}, scene {scene_index}: must be an object")
            if not nonempty_text(scene.get("visual")) or not nonempty_text(scene.get("overlay")):
                fail(f"{label}, scene {scene_index}: visual and overlay are required")
            if FACE_RE.search(scene["visual"]):
                fail(f"{label}, scene {scene_index}: visual conflicts with faceless format")
            if len(scene["overlay"]) > 120:
                fail(f"{label}, scene {scene_index}: overlay exceeds 120 characters")
            scene_count += 1

        caption = row["caption"]
        caption_chars += len(caption)
        if len(caption) < 100:
            fail(f"{label}: caption is too short")
        if row["book"].casefold() not in caption.casefold():
            fail(f"{label}: caption must attribute the book title")
        if row["author"].casefold() not in caption.casefold():
            fail(f"{label}: caption must attribute the author")
        if not any(term in caption.casefold() for term in ("inspired", "original summary", "reflection")):
            fail(f"{label}: caption needs an original-summary/reflection note")
        if COPY_RISK_RE.search(caption):
            fail(f"{label}: caption contains a full-work reproduction/download cue")

        hashtags = row["hashtags"]
        if not isinstance(hashtags, list) or not 3 <= len(hashtags) <= 8:
            fail(f"{label}: hashtags must be a list of 3–8 tags")
        if not all(isinstance(tag, str) and HASHTAG_RE.fullmatch(tag) for tag in hashtags):
            fail(f"{label}: every hashtag must use valid #Tag format")
        normalized_tags = [tag.casefold() for tag in hashtags]
        if len(set(normalized_tags)) != len(normalized_tags):
            fail(f"{label}: duplicate hashtag within item")
        all_hashtags.update(normalized_tags)

    if len(set(ids)) != EXPECTED_COUNT:
        duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
        fail(f"Duplicate IDs: {duplicates}")
    if sorted(ids) != list(range(1, EXPECTED_COUNT + 1)):
        fail("IDs must be the continuous sequence 1–30")
    if len(set(normalized_hooks)) != EXPECTED_COUNT:
        fail("Duplicate hooks after normalization")

    report = {
        "status": "PASS",
        "schema_version": "1.1.0",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "package_count": len(rows),
        "unique_ids": len(set(ids)),
        "unique_hooks": len(set(normalized_hooks)),
        "faceless_scenes": scene_count,
        "voiceover_word_count_total": voiceover_words,
        "caption_character_count_total": caption_chars,
        "unique_hashtags": len(all_hashtags),
        "checks": [
            "valid JSON and top-level array",
            "exact package count and sequential unique IDs",
            "required fields and field types",
            "three voiceover beats and three faceless scenes per item",
            "scene overlay length and faceless wording",
            "book and author attribution in every caption",
            "original-summary/reflection context note",
            "hashtag format, count and uniqueness",
        ],
        "limitations": [
            "This is structural QA, not independent fact-checking.",
            "Copyright, rights, pronunciation, accessibility and final-video quality need human review.",
            "No social post is approved or published by this workflow.",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BOOK SUMMARY QA FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
