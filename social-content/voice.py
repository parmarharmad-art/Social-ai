"""Hindi narration using Google Translate TTS; fail closed if no usable speech."""
import os
from gtts import gTTS

def _valid_audio(path):
    return os.path.isfile(path) and os.path.getsize(path) > 5000

def synth(text, path):
    if os.environ.get("FAKE_TTS") == "1":
        raise RuntimeError("FAKE_TTS is test-only")
    try:
        # gTTS uses Google's Hindi speech service; split long text to keep
        # requests within service limits while preserving natural sentence flow.
        gTTS(text=text, lang="hi", slow=False).save(path)
        if _valid_audio(path):
            return True
        print("Google Hindi TTS produced an empty or invalid audio file")
    except Exception as exc:
        print("Google Hindi TTS failed: %s" % exc)
    return False
