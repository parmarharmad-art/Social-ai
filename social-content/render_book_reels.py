#!/usr/bin/env python3
"""Adapt the 30-day book-summary library to the branded v3 animated Reel renderer."""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
def main() -> None:
    if len(sys.argv) != 4: raise SystemExit("usage: render_book_reels.py book_summaries.json assets_dir output_dir")
    source, assets, output = (Path(x).resolve() for x in sys.argv[1:])
    if not source.is_file(): raise SystemExit(f"Missing book content: {source}")
    rows = json.loads(source.read_text(encoding="utf-8"))
    if len(rows) != 30: raise SystemExit(f"Expected 30 book packages, found {len(rows)}")
    tts_path = Path(__file__).with_name("voiceover_hi.json")
    tts = json.loads(tts_path.read_text(encoding="utf-8")) if tts_path.is_file() else {}
    adapted = []
    for row in rows:
        adapted.append({"n": int(row["id"]), "h": row["hook"], "pts": row["voiceover"],
          "cta": row["cta"], "voice_cta": row["cta"], "book": row["book"],
          "author": row["author"], "theme": row["theme"], "scenes": row["scenes"],
          "tts": tts.get(str(row["id"]))})
    output.mkdir(parents=True, exist_ok=True)
    renderer = Path(__file__).with_name("gen_reels_v3.py")
    if not renderer.is_file(): raise SystemExit(f"Missing renderer: {renderer}")
    with tempfile.TemporaryDirectory(prefix="book-reels-") as temp:
        data = Path(temp) / "reels.json"
        data.write_text(json.dumps(adapted, ensure_ascii=False, indent=2), encoding="utf-8")
        env = dict(os.environ); env["BOOK_MODE"] = "1"; env["REQUIRE_VOICE"] = "1"
        subprocess.run([sys.executable, str(renderer), str(data), str(assets), str(output)],
                       check=True, timeout=14400, env=env)
    expected = [output / f"{i:02d}.mp4" for i in range(1, 31)]
    missing = [p.name for p in expected if not p.is_file() or p.stat().st_size == 0]
    if missing: raise SystemExit("Missing or empty rendered Reels: " + ", ".join(missing))
    print(f"Rendered {len(expected)} book-summary Reels into {output}")
if __name__ == "__main__": main()
