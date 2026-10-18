"""Preflight gate for social automation skills and generation inputs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SKILLS = [
    "social-media-strategy",
    "social-content-production",
    "social-publishing-automation",
    "social-analytics-optimization",
    "community-management",
    "short-form-video",
    "social-automation-engineering",
]
FILES = [
    "social-content/gen_reels.py",
    "social-content/render_ig.py",
    "social-content/voice.py",
    "social-content/assets/person_rgba.png",
    "social-content/assets/person_b.png",
]
DATASETS = [
    ("social-content/reels.json", 60, {"n", "h", "pts", "cap"}),
    ("social-content/ig.json", 30, {"n", "d", "h", "pts", "cap"}),
]

def main():
    errors = []
    for name in SKILLS:
        path = ROOT / ".github" / "skills" / name / "SKILL.md"
        if not path.is_file() or path.stat().st_size < 300:
            errors.append("Missing or incomplete skill: " + str(path.relative_to(ROOT)))
            continue
        body = path.read_text(encoding="utf-8")
        if not body.startswith("---\\n") or "\\nname:" not in body:
            errors.append("Skill frontmatter missing: " + str(path.relative_to(ROOT)))
    for item in FILES:
        path = ROOT / item
        if not path.is_file() or path.stat().st_size == 0:
            errors.append("Missing or empty input: " + item)
    for item, minimum, required in DATASETS:
        path = ROOT / item
        if not path.is_file():
            errors.append("Missing content dataset: " + item)
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(rows, list) or len(rows) < minimum:
                errors.append(f"{item} needs at least {minimum} entries")
                continue
            ids = []
            for i, row in enumerate(rows, 1):
                if not isinstance(row, dict) or not required.issubset(row):
                    errors.append(f"{item} entry {i} is missing required fields")
                    break
                if not isinstance(row["n"], int):
                    errors.append(f"{item} entry {i} has a non-integer n")
                    break
                if not isinstance(row["h"], str) or not row["h"].strip():
                    errors.append(f"{item} entry {i} has an empty heading")
                    break
                if not isinstance(row["pts"], list) or not row["pts"] or not all(isinstance(p, str) and p.strip() for p in row["pts"]):
                    errors.append(f"{item} entry {i} has invalid points")
                    break
                ids.append(row["n"])
            if len(ids) == len(rows) and len(ids) != len(set(ids)):
                errors.append(f"{item} contains duplicate n values")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{item} is invalid JSON: {exc}")
    if errors:
        print("Social automation preflight FAILED:")
        for error in errors:
            print(" - " + error)
        return 1
    print("Social automation preflight PASSED: 7 skills, 60 Reel entries, 30 card entries, and required assets verified.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
