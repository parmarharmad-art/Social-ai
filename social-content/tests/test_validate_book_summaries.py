import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validate_book_summaries.py"
SOURCE_DATA = ROOT / "book_summaries.json"


class BookSummaryValidatorTests(unittest.TestCase):
    def run_validator(self, mutate=None):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            shutil.copy2(VALIDATOR, work / "validate_book_summaries.py")
            rows = json.loads(SOURCE_DATA.read_text(encoding="utf-8"))
            if mutate:
                mutate(rows)
            (work / "book_summaries.json").write_text(
                json.dumps(rows, ensure_ascii=False), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(work / "validate_book_summaries.py")],
                text=True, capture_output=True, check=False,
            )
            report = work / "book-summary-quality-report.json"
            return result, report.exists()

    def test_repository_content_passes(self):
        result, report_exists = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report_exists)
        self.assertIn('"status": "PASS"', result.stdout)

    def test_duplicate_id_is_rejected(self):
        def mutate(rows):
            rows[1]["id"] = rows[0]["id"]
        result, report_exists = self.run_validator(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate IDs", result.stderr)
        self.assertFalse(report_exists)

    def test_missing_scene_is_rejected(self):
        def mutate(rows):
            rows[0]["scenes"] = rows[0]["scenes"][:2]
        result, report_exists = self.run_validator(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly 3 faceless scenes", result.stderr)
        self.assertFalse(report_exists)

    def test_missing_author_attribution_is_rejected(self):
        def mutate(rows):
            rows[0]["caption"] = rows[0]["caption"].replace(rows[0]["author"], "Unknown Author")
        result, report_exists = self.run_validator(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must attribute the author", result.stderr)
        self.assertFalse(report_exists)


if __name__ == "__main__":
    unittest.main(verbosity=2)
