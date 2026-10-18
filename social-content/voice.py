"""Text-to-speech helper. Tries edge-tts (Indian English voice), then gTTS, then espeak-ng.
Set FAKE_TTS=1 to generate placeholder tones (used only for testing the timeline)."""
import asyncio
import os
import subprocess

VOICE = os.environ.get("REEL_VOICE", "en-IN-PrabhatNeural")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(out.stdout.strip())


def synth(text, path):
    """Write speech for `text` to `path` (mp3/wav). Returns True on success."""
    if os.environ.get("FAKE_TTS") == "1":
        secs = max(1.0, 0.075 * len(text))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=frequency=180:duration=%.2f" % secs, "-af", "volume=0.2", path], check=True)
        return True
    try:
        import edge_tts
        asyncio.run(edge_tts.Communicate(text, VOICE, rate="+4%").save(path))
        if os.path.getsize(path) > 1000:
            return True
    except Exception as e:  # noqa: BLE001
        print("edge-tts failed:", e)
    try:
        from gtts import gTTS
        gTTS(text, lang="en", tld="co.in").save(path)
        if os.path.getsize(path) > 1000:
            return True
    except Exception as e:  # noqa: BLE001
        print("gTTS failed:", e)
    try:
        wav = path.rsplit(".", 1)[0] + ".wav"
        subprocess.run(["espeak-ng", "-v", "en-in", "-s", "160", "-w", wav, text], check=True)
        if wav != path:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, path], check=True)
        return True
    except Exception as e:  # noqa: BLE001
        print("espeak failed:", e)
    return False
