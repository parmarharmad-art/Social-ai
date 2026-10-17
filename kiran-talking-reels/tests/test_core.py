from PIL import Image
import pytest
from src.validation import validate_image
from src.script_generator import make_script,make_caption
def test_invalid_image(tmp_path):
 p=tmp_path/"bad.jpg"; p.write_text("not image")
 with pytest.raises(ValueError): validate_image(p)
def test_missing_image(tmp_path):
 with pytest.raises(ValueError): validate_image(tmp_path/"missing.png")
def test_valid_image(tmp_path):
 p=tmp_path/"valid.png"; Image.new("RGB",(50,50)).save(p); validate_image(p)
def test_hindi_script():
 assert "AI" in make_script("WhatsApp automation")
def test_empty_topic():
 with pytest.raises(ValueError): make_script("")
def test_caption():
 assert "#AIAutomation" in make_caption("AI workflow","test")
