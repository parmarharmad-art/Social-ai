"""Preflight check: separate skill files and social-content generator inputs."""
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
INPUTS = [
    "social-content/reels.json",
    "social-content/ig.json",
    "social-content/gen_reels.py",
    "social-content/render_ig.py",
    "social-content/voice.py",
    "social-content/assets/person_rgba.png",
    "social-content/assets/person_b.png",
]

def main():
    errors = []
    for name in SKILLS:
        path = ROOT / ".github" / "skills" / name / "SKILL.md"
        if not path.is_file() or path.stat().st_size < 300:
            errors.append("Missing or incomplete skill: " + str(path.relative_to(ROOT)))
    for item in INPUTS:
        path = ROOT / item
        if not path.is_file() or path.stat().st_size == 0:
            errors.append("Missing or empty generator input: " + item)
    if errors:
        print("Social automation preflight FAILED")
        print("\\n".join("- " + error for error in errors))
        return 1
    print("Social automation preflight PASSED: seven separate skills and all generator inputs exist.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
