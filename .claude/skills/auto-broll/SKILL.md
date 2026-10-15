---
name: auto-broll
description: Add B-roll to a supplied video using the repository's auto_broll.py script. Use when the user asks to auto-generate B-roll, run auto_broll.py, or process a video such as VID-20241101-WA0000.mp4 into an output MP4.
---

# Auto B-roll video workflow

Use this skill to run the project's existing `auto_broll.py` workflow on a user-supplied video.

## Expected command

```bash
python -m pip install openai-whisper requests
python auto_broll.py "VID-20241101-WA0000.mp4" "output.mp4"
```

## Procedure

1. Inspect the repository and current working directory first. Confirm that `auto_broll.py` exists and identify the actual input video path. Do not assume the example filename exists.
2. Check Python and FFmpeg availability (`python --version`, `ffmpeg -version`). Whisper commonly relies on FFmpeg. If FFmpeg is missing, explain how to install it for the current operating system.
3. Install dependencies using `python -m pip install openai-whisper requests` in the project's active environment. Do not install packages globally if a virtual environment is available.
4. Run the script with quoted input and output paths:
   `python auto_broll.py "<input-video.mp4>" "<output-video.mp4>"`
5. If execution fails, capture the exact error and diagnose it. Check whether the script expects different arguments, whether the input exists, whether FFmpeg is installed, and whether any external API key or network access is required. Never claim success without checking the process exit status and confirming that the output file exists and has non-zero size.
6. Preserve the original input video. Do not overwrite it. If the requested output already exists, ask before replacing it or choose a new output filename.
7. Summarize what ran, report any blockers accurately, and provide the output file path/link only if the output file was actually created and verified.

## Important constraints

- Installing `openai-whisper` may download model weights on first use and can take time or disk space.
- This skill does not itself provide a B-roll footage library or guarantee that `auto_broll.py` can find/download footage. Inspect the script to understand its current implementation before promising results.
- Do not expose API keys, tokens, or other secrets in logs or replies.
- If `auto_broll.py` is absent, do not pretend the command works. Offer to create or repair the script in the repository, based on the intended B-roll behavior.
