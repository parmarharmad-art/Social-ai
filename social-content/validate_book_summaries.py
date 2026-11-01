#!/usr/bin/env python3
"""Deterministic QA for the separate 30-day faceless book-summary library."""
import json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "book_summaries.json"
REPORT = ROOT / "book-summary-quality-report.json"
REQUIRED = {"id","book","author","theme","hook","voiceover","caption","scenes","cta","hashtags"}
def fail(msg): raise ValueError(msg)
def main():
    rows=json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(rows,list) or len(rows)!=30: fail("Expected exactly 30 content packages")
    ids=[]; hooks=[]
    for i,row in enumerate(rows,1):
        if not isinstance(row,dict) or not REQUIRED.issubset(row): fail(f"Entry {i}: missing required fields")
        ids.append(row["id"]); hooks.append(re.sub(r"[^a-z0-9]+"," ",row["hook"].lower()).strip())
        for key in ("book","author","theme","hook","caption","cta"):
            if not isinstance(row[key],str) or not row[key].strip(): fail(f"Entry {i}: invalid {key}")
        if not isinstance(row["voiceover"],list) or len(row["voiceover"])!=3 or not all(isinstance(x,str) and x.strip() for x in row["voiceover"]): fail(f"Entry {i}: voiceover must have 3 non-empty beats")
        if not isinstance(row["scenes"],list) or len(row["scenes"])!=3: fail(f"Entry {i}: expected 3 faceless scenes")
        for scene in row["scenes"]:
            if not isinstance(scene,dict) or not scene.get("visual") or not scene.get("overlay"): fail(f"Entry {i}: invalid scene")
            if re.search(r"\b(face reveal|show face|talking head)\b",scene["visual"],re.I): fail(f"Entry {i}: non-faceless visual")
        if not isinstance(row["hashtags"],list) or len(row["hashtags"])<3 or not all(x.startswith("#") for x in row["hashtags"]): fail(f"Entry {i}: invalid hashtags")
        if len(row["caption"])<100: fail(f"Entry {i}: caption too short")
        if row["book"].lower() not in row["caption"].lower() or row["author"].lower() not in row["caption"].lower(): fail(f"Entry {i}: book/author attribution missing")
        if not any(x in row["caption"].lower() for x in ("inspired","original summary","reflection")): fail(f"Entry {i}: originality/context note missing")
        if len(" ".join(row["voiceover"]))<120: fail(f"Entry {i}: voiceover too short")
    if len(set(ids))!=30: fail("Duplicate IDs")
    if len(set(hooks))!=30: fail("Duplicate hooks")
    report={"status":"PASS","count":len(rows),"unique_ids":len(set(ids)),"unique_hooks":len(set(hooks)),"faceless_scenes":sum(len(x["scenes"]) for x in rows),"attribution":"book and author required in every caption","note":"Automated structural QA only; human editorial, rights, pronunciation and final-video review remain required."}
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("BOOK SUMMARY QA FAILED:",exc); sys.exit(1)
