"""Hindi narration. Natural neural voice only (edge-tts), with voice fallbacks and bounded retries.
Robotic Google TTS (gTTS) is NOT used unless ALLOW_GTTS_FALLBACK=1.
Returns False when no neural audio could be made, so callers fail closed.
"""
import asyncio, os, time
VOICE=os.environ.get("REEL_VOICE","hi-IN-MadhurNeural")
RATE=os.environ.get("REEL_TTS_RATE","-4%")
PITCH=os.environ.get("REEL_TTS_PITCH","+0Hz")
OTHER="hi-IN-SwaraNeural" if "Madhur" in VOICE else "hi-IN-MadhurNeural"
FALLBACKS=[v for v in os.environ.get("REEL_VOICE_FALLBACKS",OTHER).split(",") if v]
def _valid_audio(path): return os.path.isfile(path) and os.path.getsize(path)>1500
def _edge(text,path,voice):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text,voice,rate=RATE,pitch=PITCH).save(path))
    return _valid_audio(path)
def _gtts(text,path,voice=None):
    from gtts import gTTS
    gTTS(text=text,lang="hi",slow=False).save(path)
    return _valid_audio(path)
def synth(text,path):
    if os.environ.get("FAKE_TTS")=="1": raise RuntimeError("FAKE_TTS is test-only")
    plan=[("edge-tts:"+v,_edge,v) for v in [VOICE]+FALLBACKS]
    if os.environ.get("ALLOW_GTTS_FALLBACK")=="1": plan.append(("gTTS",_gtts,None))
    for name,fn,v in plan:
        for attempt in (1,2,3):
            try:
                if fn(text,path,v): print("voice ok:",name); return True
                print("%s empty audio (attempt %d)"%(name,attempt))
            except Exception as exc: print("%s failed (attempt %d): %s"%(name,attempt,exc))
            time.sleep(2*attempt)
    return False
