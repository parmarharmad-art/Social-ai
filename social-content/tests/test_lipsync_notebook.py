import json
import unittest
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / "Free_Hindi_Photo_LipSync_Colab.ipynb"


class LipSyncNotebookContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.cells = ["".join(cell.get("source", [])) for cell in cls.notebook["cells"]]
        cls.all_source = "\n".join(cls.cells)

    def test_notebook_json_and_expected_cells(self):
        self.assertGreaterEqual(self.notebook.get("nbformat", 0), 4)
        self.assertGreaterEqual(len(self.cells), 6)

    def test_only_current_upload_is_selected(self):
        upload = self.cells[1]
        self.assertIn("files.upload()", upload)
        self.assertIn("uploaded_images = [name for name in uploaded", upload)
        self.assertIn("portrait_for_lipsync.jpg", upload)
        self.assertNotIn("Path('/content').iterdir()", upload)

    def test_tts_is_installed_and_generated_before_model_download(self):
        setup = self.cells[3]
        self.assertIn("'edge-tts'", setup)
        self.assertLess(setup.index("Generating Hindi narration"), setup.index("scripts/download_models.sh"))
        self.assertIn("edge_tts.Communicate(script, 'hi-IN-SwaraNeural')", setup)

    def test_inference_uses_generated_audio_and_normalized_portrait(self):
        inference = self.cells[4]
        self.assertIn("portrait_for_lipsync.jpg", inference)
        self.assertIn("hindi_narration.mp3", inference)
        self.assertIn("hindi_narration_16k_mono.wav", inference)
        self.assertIn("'inference.py'", inference)
        self.assertIn("'--driven_audio'", inference)
        self.assertIn("'--source_image'", inference)
        self.assertIn("subprocess.run(cmd, cwd=str(repo), check=True)", inference)
        self.assertNotIn("images[0].name", inference)
        self.assertNotIn("audio_import json", inference)

    def test_mp4_requires_audio_video_duration_and_decode_validation(self):
        inference = self.cells[4]
        for required in (
            "'video' in stream_types",
            "'audio' in stream_types",
            "duration_tolerance",
            "decode.returncode == 0",
            "talking_photo_hindi.mp4",
            "shutil.copy2(output_path, final_output)",
        ):
            self.assertIn(required, self.all_source)

    def test_download_cell_refuses_missing_or_empty_output(self):
        download = self.cells[5]
        self.assertIn("talking_photo_hindi.mp4", download)
        self.assertIn("stat().st_size > 1000", download)


if __name__ == "__main__":
    unittest.main()
