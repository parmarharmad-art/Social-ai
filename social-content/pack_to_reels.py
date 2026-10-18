"""Convert the AI content-pack JSON into the schema used by gen_reels.py."""
import argparse
import json
import re
from pathlib import Path

def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()

def short_points(item):
    raw = str(item.get("script_or_body", ""))
    candidates = []
    for line in raw.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        line = clean(line)
        if len(line) >= 8 and line.lower() not in {"script", "on-screen text", "visual"}:
            candidates.append(line)
    if not candidates:
        candidates = [clean(item.get("visual_brief")), clean(item.get("cta"))]
    # Keep the visual readable in the existing Reel template.
    points = []
    for line in candidates:
        if len(line) > 62:
            line = line[:59].rsplit(" ", 1)[0] + "…"
        if line and line not in points:
            points.append(line)
        if len(points) == 4:
            break
    return points or ["One clear idea", "Show the steps", "End with a useful CTA"]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    src = json.loads(Path(a.input).read_text(encoding="utf-8"))
    items = src.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit("ERROR: content pack contains no items")
    converted = []
    for n, item in enumerate(items, 1):
        hook = clean(item.get("hook")) or clean(item.get("topic"))
        caption = clean(item.get("caption"))
        cta = clean(item.get("cta"))
        tags = " ".join(clean(t).replace(" ", "") for t in item.get("hashtags", []) if clean(t))
        full_caption = "\n\n".join(x for x in (caption, cta, tags) if x)
        if not hook or not full_caption:
            raise SystemExit(f"ERROR: item {n} is missing hook or caption")
        converted.append({"n": n, "h": hook[:100], "pts": short_points(item), "cap": full_caption})
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(converted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: converted {len(converted)} AI draft items to Reel renderer input at {out}")
if __name__ == "__main__":
    main()
