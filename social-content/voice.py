"""Reliable local speech synthesis for the social-content workflow.

The CI workflow selects REEL_TTS_PROVIDER=espeak so every Reel can render
without waiting on external TTS services. Hindi is preferred; Indian English
is the local fallback. Narration text is spoken as supplied.
"""
import os
import subprocess

TTS_LANGUAGE = os.environ.get("REEL_TTS_LANGUAGE", "hi")


def _valid_audio(path):
    return os.path.isfile(path) and os.path.getsize(path) > 1000


def synth(text, path):
    """Write real speech to path; return True only when audio was produced."""
    if os.environ.get("FAKE_TTS") == "1":
        raise RuntimeError("FAKE_TTS is test-only and cannot be used for published Reels")

    wav = path.rsplit(".", 1)[0] + ".wav"
    preferred = ["hi", "en-in"] if TTS_LANGUAGE.lower().startswith("hi") else ["en-in", "hi"]
    for lang in preferred:
        try:
            subprocess.run(
                ["espeak-ng", "-v", lang, "-s", "150", "-w", wav, text],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                timeout=20,
            )
            if not _valid_audio(wav):
                continue
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", wav, path],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                timeout=20,
            )
            if _valid_audio(path):
                return True
        except (subprocess.SubprocessError, OSError) as exc:
            print("local TTS voice %s failed: %s" % (lang, exc))
    return False
