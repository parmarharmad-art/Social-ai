"""Audit the planned social content against the 7 social-media skill standards.

This is a deterministic QA gate, not an LLM: it verifies the current content library
and writes a machine-readable report. It does not pretend to generate new ideas or
measure live performance.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "content-quality-report.json"
DATASETS = {
    "instagram_posts": (ROOT / "ig.json", 30),
    "reels": (ROOT / "reels.json", 60),
}
CTA_TERMS = ("comment", "save", "share", "follow", "try", "start", "download",
             "reply", "send", "learn", "check", "book", "visit", "tell", "ask")
GENERIC_HOOKS = {"tips", "social media", "ai tools", "automation", "content"}
def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()
def audit_dataset(name, path, minimum):
    errors, warnings, rows_out = [], [], []
    if not path.exists():
        return {"dataset": name, "count": 0, "passed": False,
                "errors": ["dataset missing"], "warnings": []}
    rows = json.loads(path.read_text(encoding="utf-8"))
    if len(rows) < minimum:
        errors.append(f"Expected at least {minimum} entries; found {len(rows)}")
    hooks = [norm(r.get("h", "")) for r in rows]
    duplicates = [k for k, n in Counter(hooks).items() if k and n > 1]
    if duplicates:
        errors.append("Duplicate hooks: " + ", ".join(duplicates[:10]))
    missing_fields = []
    no_cta = []
    short_caption = []
    for i, row in enumerate(rows, 1):
        required = ("h", "pts", "cap")
        absent = [k for k in required if not row.get(k)]
        if absent:
            missing_fields.append(f"entry {i}: {','.join(absent)}")
        caption = str(row.get("cap", "")).strip()
        if len(caption) < 60:
            short_caption.append(i)
        if not any(term in norm(caption) for term in CTA_TERMS):
            no_cta.append(i)
    if missing_fields:
        errors.append("Missing required fields: " + "; ".join(missing_fields[:10]))
    if short_caption:
        warnings.append("Captions under 60 characters at entries: " + ", ".join(map(str, short_caption[:20])))
    if no_cta:
        warnings.append("No recognizable CTA language at entries: " + ", ".join(map(str, no_cta[:20])))
    if any(norm(r.get("h", "")) in GENERIC_HOOKS for r in rows):
        warnings.append("One or more hooks are too generic")
    return {"dataset": name, "count": len(rows), "passed": not errors,
            "unique_hooks": len(set(hooks)), "errors": errors, "warnings": warnings,
            "checks": {"required_fields": not missing_fields,
                       "unique_hooks": not duplicates,
                       "captions_reviewed": len(rows),
                       "cta_coverage": round((len(rows)-len(no_cta))/max(len(rows),1), 3)}}
def main():
    reports = [audit_dataset(name, path, minimum)
               for name, (path, minimum) in DATASETS.items()]
    skill_names = [
        "social-media-strategy", "social-content-production",
        "social-publishing-automation", "social-analytics-optimization",
        "community-management", "short-form-video",
        "social-automation-engineering",
    ]
    skill_status = {}
    for name in skill_names:
        p = ROOT.parent / ".github" / "skills" / name / "SKILL.md"
        skill_status[name] = p.exists() and p.stat().st_size >= 300
    report = {
        "audit_type": "deterministic_content_quality_gate",
        "note": "This checks the existing content library; it does not prove that skills were invoked by an AI model or that posts performed well.",
        "skills_present": skill_status,
        "all_seven_skills_present": all(skill_status.values()),
        "datasets": reports,
        "passed": all(skill_status.values()) and all(r["passed"] for r in reports),
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["passed"]:
        raise SystemExit("Content quality gate failed; review content-quality-report.json")
if __name__ == "__main__":
    main()
