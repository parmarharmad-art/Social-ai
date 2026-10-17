from PIL import Image
import pytest
from src.validation import validate_image
from src.script_generator import make_script, make_caption
from src.subtitles import make_srt, split_caption_lines


def test_invalid_image(tmp_path):
    p = tmp_path / "bad.jpg"
    p.write_text("not image")
    with pytest.raises(ValueError):
        validate_image(p)


def test_missing_image(tmp_path):
    with pytest.raises(ValueError):
        validate_image(tmp_path / "missing.png")


def test_valid_image(tmp_path):
    p = tmp_path / "valid.png"
    Image.new("RGB", (50, 50)).save(p)
    validate_image(p)


def test_hindi_script():
    assert "AI" in make_script("WhatsApp automation")


def test_empty_topic():
    with pytest.raises(ValueError):
        make_script("")


def test_caption():
    assert "#AIAutomation" in make_caption("AI workflow", "test")


def test_srt_contains_timing_and_script():
    srt = make_srt("पहला वाक्य। दूसरा वाक्य।", 15)
    assert "00:00:00,000 -->" in srt
    assert "पहला वाक्य" in srt
    assert srt.rstrip().endswith("दूसरा वाक्य।")


def test_srt_rejects_empty_script():
    with pytest.raises(ValueError):
        make_srt(" ", 15)


def test_long_caption_wraps_at_word_boundaries():
    lines = split_caption_lines("This is a long sentence with enough words to wrap into more than one subtitle line.")
    assert len(lines) > 1
    assert all(len(line) <= 46 for line in lines)
