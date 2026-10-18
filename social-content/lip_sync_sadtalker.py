#!/usr/bin/env python3
"""Generate a talking-photo video with a locally installed SadTalker checkout.

This is an optional adapter, not a hosted/free-GPU service. It requires the
SadTalker repository, its model checkpoints, its Python dependencies, and a
working inference environment. It fails clearly rather than returning a fake
or silent "lip-sync" video.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="Animate one portrait image from an audio file using SadTalker.")
    p.add_argument("--image", required=True, help="Input portrait image (jpg/png)")
    p.add_argument("--audio", required=True, help="Hindi narration audio (wav/mp3)")
    p.add_argument("--sadtalker-dir", default=os.environ.get("SADTALKER_DIR", ""),
                   help="Path to an installed OpenTalker/SadTalker checkout")
    p.add_argument("--output", required=True, help="Destination MP4 path")
    p.add_argument("--python", default=sys.executable, help="Python executable for the SadTalker environment")
    p.add_argument("--enhancer", default="", choices=["", "gfpgan"], help="Optional face enhancer")
    args = p.parse_args()

    image = Path(args.image).expanduser().resolve()
    audio = Path(args.audio).expanduser().resolve()
    root = Path(args.sadtalker_dir).expanduser().resolve() if args.sadtalker_dir else None
    output = Path(args.output).expanduser().resolve()

    if not image.is_file() or image.stat().st_size == 0:
        p.error("Input image does not exist or is empty: %s" % image)
    if not audio.is_file() or audio.stat().st_size == 0:
        p.error("Input audio does not exist or is empty: %s" % audio)
    if root is None or not (root / "inference.py").is_file():
        p.error("SadTalker checkout not found. Set SADTALKER_DIR to a directory containing inference.py.")
    output.parent.mkdir(parents=True, exist_ok=True)

    result_dir = output.parent / (output.stem + "_sadtalker")
    result_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        args.python, str(root / "inference.py"),
        "--driven_audio", str(audio),
        "--source_image", str(image),
        "--result_dir", str(result_dir),
        "--still",
        "--preprocess", "full",
    ]
    if args.enhancer:
        cmd.extend(["--enhancer", args.enhancer])

    print("Running SadTalker inference. This requires compatible model weights and usually a GPU for practical speed.")
    subprocess.run(cmd, cwd=str(root), check=True)

    candidates = sorted(
        (f for f in result_dir.rglob("*.mp4") if f.is_file() and f.stat().st_size > 1000),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise RuntimeError("SadTalker finished but produced no MP4. Check its logs, checkpoints, and runtime compatibility.")

    generated = candidates[0]
    if generated.resolve() != output:
        import shutil
        shutil.copy2(generated, output)
    if not output.is_file() or output.stat().st_size <= 1000:
        raise RuntimeError("Output MP4 validation failed: %s" % output)

    # A non-empty file alone is not enough: verify that ffprobe can read both
    # video and audio streams before reporting success.
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found. Install ffmpeg, then rerun to validate the MP4 streams.")
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-of", "csv=p=0", str(output)],
        check=True, capture_output=True, text=True,
    )
    stream_lines = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
    has_video = any(line.startswith("video,") or line == "video" for line in stream_lines)
    has_audio = any(line.startswith("audio,") or line == "audio" for line in stream_lines)
    if not has_video or not has_audio:
        raise RuntimeError("Output failed stream validation. ffprobe streams: %r" % stream_lines)
    print("SUCCESS: validated video+audio MP4: %s (%d bytes)" % (output, output.stat().st_size))


if __name__ == "__main__":
    main()
