"""Neural Hindi speech synthesis for Reels using Edge TTS."""
import os
import subprocess

VOICE = os.environ.get("REEL_TTS_VOICE", "hi-IN-MadhurNeural")
RATE = os.environ.get("REEL_TTS_RATE", "-8%")


def _valid_audio(path):
    return os.path.isfile(path) and os.path.getsize(path) > 5000


def synth(text, path):
    """Generate neural Hindi narration. Never silently fall back to robotic TTS."""
    if os.environ.get("FAKE_TTS") == "1":
        raise RuntimeError("FAKE_TTS is test-only")
    cmd = [
        "edge-tts", "--voice", VOICE, "--rate=" + RATE,
        "--text", text, "--write-media", path,
    ]
    try:
        result = subprocess.run(
            cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=90,
        )
        if result.returncode != 0:
            print("Neural TTS exit=%s stderr=%s" % (result.returncode, (result.stderr or result.stdout)[-1800:]))
            return False
        if _valid_audio(path):
            return True
        print("Neural TTS produced an empty or invalid audio file")
        return False
    except (subprocess.SubprocessError, OSError) as exc:
        print("Neural Hindi TTS failed: %s" % exc)
        return False
