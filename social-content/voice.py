"""Hindi/Hinglish narration. Tries a neural voice (edge-tts) first, falls back to Google TTS (gTTS).
Fails closed: returns False when no usable speech was produced, so the Reel is never published silent.
Env: REEL_VOICE (default hi-IN-MadhurNeural; female: hi-IN-SwaraNeural), REEL_TTS_RATE (default +0%)."""
import asyncio
import os
import time

VOICE = os.environ.get("REEL_VOICE", "hi-IN-MadhurNeural")
RATE = os.environ.get("REEL_TTS_RATE", "+0%")


def _valid_audio(path):
    return os.path.isfile(path) and os.path.getsize(path) > 1500


def _edge(text, path):
    import edge_tts  # optional dependency: pip install edge-tts
    asyncio.run(edge_tts.Communicate(text, VOICE, rate=RATE).save(path))
    return _valid_audio(path)


def _gtts(text, path):
    from gtts import gTTS
    gTTS(text=text, lang="hi", slow=False).save(path)
    return _valid_audio(path)


def synth(text, path):
    if os.environ.get("FAKE_TTS") == "1":
        raise RuntimeError("FAKE_TTS is test-only")
    for name, fn in (("edge-tts", _edge), ("gTTS", _gtts)):
        for attempt in (1, 2):
            try:
                if fn(text, path):
                    return True
                print("%s produced an empty audio file (attempt %d)" % (name, attempt))
            except Exception as exc:  # noqa: BLE001
                print("%s failed (attempt %d): %s" % (name, attempt, exc))
            time.sleep(1.5 * attempt)
    return False
