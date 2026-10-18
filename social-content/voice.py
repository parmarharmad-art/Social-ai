"""Text-to-speech helper with configurable Indian voice providers.

Set REEL_VOICE (default: hi-IN-SwaraNeural) to select an Edge TTS voice.
Falls back to Google TTS in Hindi, then available espeak-ng voices.
Note: the narration text is spoken as supplied; this module does not translate it.
Set FAKE_TTS=1 only for timeline tests (it creates a tone, not speech).
"""
import asyncio
import os
import subprocess

VOICE = os.environ.get("REEL_VOICE", "hi-IN-SwaraNeural")
TTS_LANGUAGE = os.environ.get("REEL_TTS_LANGUAGE", "hi")


def _valid_audio(path):
    return os.path.isfile(path) and os.path.getsize(path) > 1000


def synth(text, path):
    """Write speech for text to path; return True only if a non-empty audio file exists."""
    if os.environ.get("FAKE_TTS") == "1":
        secs = max(1.0, 0.075 * len(text))
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
             "sine=frequency=180:duration=%.2f" % secs, "-af", "volume=0.2", path],
            check=True,
        )
        return _valid_audio(path)

    try:
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, VOICE, rate="+4%").save(path))
        if _valid_audio(path):
            return True
    except Exception as e:  # noqa: BLE001
        print("edge-tts failed:", e)

    try:
        from gtts import gTTS
        gTTS(text, lang=TTS_LANGUAGE, tld="co.in").save(path)
        if _valid_audio(path):
            return True
    except Exception as e:  # noqa: BLE001
        print("gTTS failed:", e)

    # espeak language packs vary by runner; try Hindi, then Indian English.
    wav = path.rsplit(".", 1)[0] + ".wav"
    for lang in ("hi", "en-in"):
        try:
            subprocess.run(
                ["espeak-ng", "-v", lang, "-s", "150", "-w", wav, text],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            if _valid_audio(wav):
                if wav != path:
                    subprocess.run(
                        ["ffmpeg", "-y", "-loglevel", "error", "-i", wav, path],
                        check=True,
                    )
                if _valid_audio(path):
                    return True
        except Exception as e:  # noqa: BLE001
            print("espeak-ng voice %s failed: %s" % (lang, e))
    return False
