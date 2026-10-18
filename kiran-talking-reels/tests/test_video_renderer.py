import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from src.validation import ffprobe_info
from src.video_renderer import render


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools not installed")
def test_render_produces_valid_vertical_mp4(tmp_path):
    image_path = tmp_path / "photo.png"
    audio_path = tmp_path / "voice.wav"
    output_path = tmp_path / "output.mp4"
    Image.new("RGB", (320, 320), (20, 40, 80)).save(image_path)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-c:a", "pcm_s16le", str(audio_path)],
        check=True, capture_output=True, text=True,
    )
    render(image_path, audio_path, output_path, 2)
    assert output_path.exists() and output_path.stat().st_size > 1000
    info = ffprobe_info(output_path)
    video = [s for s in info["streams"] if s.get("codec_type") == "video"]
    audio = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    assert video and video[0]["width"] == 720 and video[0]["height"] == 1280
    assert audio


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools not installed")
def test_render_can_use_talking_video_source(tmp_path):
    image_path = tmp_path / "photo.png"
    audio_path = tmp_path / "voice.wav"
    source_video = tmp_path / "talking_source.mp4"
    output_path = tmp_path / "talking_output.mp4"
    Image.new("RGB", (320, 320), (20, 40, 80)).save(image_path)
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-framerate", "25", "-i", str(image_path),
         "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source_video)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-c:a", "pcm_s16le", str(audio_path)],
        check=True, capture_output=True, text=True,
    )
    render(image_path, audio_path, output_path, 2, talking_video_path=source_video)
    info = ffprobe_info(output_path)
    video = [s for s in info["streams"] if s.get("codec_type") == "video"]
    audio = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    assert output_path.exists() and output_path.stat().st_size > 1000
    assert video and video[0]["width"] == 720 and video[0]["height"] == 1280
    assert audio
