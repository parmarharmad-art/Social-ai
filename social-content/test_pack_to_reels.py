import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("pack_to_reels.py")

class PackToReelsTests(unittest.TestCase):
    def run_converter(self, pack):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        source, target = root / "pack.json", root / "reels.json"
        source.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(target)],
            text=True, capture_output=True,
        )
        result = json.loads(target.read_text(encoding="utf-8")) if target.exists() else None
        self.tmp.cleanup()
        return proc, result

    def test_valid_pack_maps_fields_and_preserves_unicode(self):
        proc, result = self.run_converter({"items": [{
            "topic": "AI automation", "hook": "Hindi hook — शुरू करें",
            "script_or_body": "Step one: plan the post\nStep two: create the visual\nStep three: review",
            "caption": "A practical caption with enough detail for readers.",
            "cta": "Save this", "hashtags": ["#AI", "#सोशलमीडिया"],
        }]})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["n"], 1)
        self.assertIn("शुरू करें", result[0]["h"])
        self.assertEqual(len(result[0]["pts"]), 3)
        self.assertIn("#सोशलमीडिया", result[0]["cap"])
        self.assertEqual(result[0]["cta"], "Save this")
        self.assertTrue(result[0]["voice_cta"])

    def test_empty_items_fails_cleanly(self):
        proc, result = self.run_converter({"items": []})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no items", proc.stderr)
        self.assertIsNone(result)

    def test_missing_caption_fails_cleanly(self):
        proc, result = self.run_converter({"items": [{
            "hook": "Useful hook", "script_or_body": "A step that explains a useful process.",
            "cta": "Save", "hashtags": ["#AI"]
        }]})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("missing hook or caption", proc.stderr)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main(verbosity=2)
