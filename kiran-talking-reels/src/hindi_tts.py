from pathlib import Path
def make_audio(text,output_path):
 if not text.strip(): raise ValueError("Script is empty.")
 try: from gtts import gTTS
 except ImportError as e: raise RuntimeError("Install requirements.txt or upload a recording.") from e
 try: gTTS(text=text,lang="hi",slow=False).save(str(output_path))
 except Exception as e: raise RuntimeError("Hindi TTS failed; check internet or upload a recording.") from e
 if not Path(output_path).exists() or Path(output_path).stat().st_size<1000: raise RuntimeError("TTS produced no usable audio.")
