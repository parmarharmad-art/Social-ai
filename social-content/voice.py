"""Neural Hindi speech synthesis for social-content Reels.

Uses Microsoft's Edge neural Hindi voices through edge-tts. If neural synthesis
fails, return failure rather than silently falling back to robotic eSpeak.
"""
import os
import subprocess

VOICE = os.environ.get("REEL_TTS_VOICE", "hi-IN-MadhurNeural")
RATE = os.environ.get("REEL_TTS_RATE", "-8%")


def _valid_audio(path):
    return os.path.isfile(path) and os.path.getsize(path) > 5000


def synth(text, path):
    """Write neural Hindi speech to path; return True only for valid output."""
    if os.environ.get("FAKE_TTS") == "1":
        raise RuntimeError("FAKE_TTS is test-only and cannot be used for Reels")

    try:
        subprocess.run(
            ["edge-tts", "--voice", VOICE, "--rate", RATE,
             "--text", text, "--write-media", path],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=90,
        )
        if _valid_audio(path):
            return True
        print("Neural TTS produced an empty or invalid audio file")
    except (subprocess.SubprocessError, OSError) as exc:
        print("Neural Hindi TTS failed: %s" % exc)
    return False
