import shutil, subprocess, tempfile
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from src.script_generator import make_script, make_caption
from src.validation import validate_image, ffprobe_info
from src.hindi_tts import make_audio
load_dotenv()
ROOT=Path(__file__).parent
OUT=ROOT/"outputs"; OUT.mkdir(exist_ok=True)
st.set_page_config(page_title="Kiran Kumar • AI Talking Reels",page_icon="🎬")
st.title("🎬 Kiran Kumar • AI Talking Reels")
st.caption("Kiran Kumar • AI Automation")
st.warning("This MVP preserves your photo and adds narration/zoom. It does NOT animate lips; real lip-sync needs a separately configured licensed API or GPU engine.")
photo=st.file_uploader("Upload personal photo",type=["jpg","jpeg","png","webp"])
topic=st.text_input("Reel topic",placeholder="WhatsApp lead follow-up automation")
duration=st.select_slider("Duration target (seconds)",options=[15,30,45,60],value=30)
language=st.selectbox("Language",["Hindi","Hinglish"])
script=st.text_area("Review or edit script (optional)",height=140)
voice=st.radio("Narration source",["Generate Hindi voice (internet required)","Upload recorded voiceover"])
audio_upload=st.file_uploader("Voiceover audio",type=["mp3","wav","m4a"]) if voice.startswith("Upload") else None
music=st.file_uploader("Optional background music",type=["mp3","wav","m4a"])
if st.button("Generate Reel",type="primary"):
 if not photo: st.error("Upload a photo first.")
 elif not topic.strip() and not script.strip(): st.error("Enter a topic or script.")
 else:
  work=Path(tempfile.mkdtemp(prefix="kiran_reel_"))
  try:
   img=work/"photo.png"; img.write_bytes(photo.getvalue()); validate_image(img)
   final_script=script.strip() or make_script(topic,duration,language)
   st.subheader("Script preview"); st.write(final_script)
   (OUT/"latest_script.txt").write_text(final_script,encoding="utf-8")
   audio=work/"voice.mp3"
   if voice.startswith("Upload"):
    if not audio_upload: raise ValueError("Upload a recorded voiceover.")
    audio.write_bytes(audio_upload.getvalue())
   else: make_audio(final_script,audio)
   music_path=None
   if music:
    music_path=work/"music"; music_path.write_bytes(music.getvalue())
   output=OUT/"kiran_talking_reel.mp4"
   render(img,audio,output,music_path)
   info=ffprobe_info(output)
   st.success("MP4 generated; basic stream validation passed.")
   st.video(str(output)); st.download_button("Download MP4",output.read_bytes(),"kiran_talking_reel.mp4","video/mp4")
   caption=make_caption(topic or "AI workflow",final_script)
   st.text_area("Caption",caption,height=150)
   st.download_button("Download caption",caption,"caption.txt","text/plain")
   st.download_button("Download script",final_script,"hindi_script.txt","text/plain")
   st.json(info)
   st.warning("Manually review framing, audio, duration and spelling. Lip-sync and subtitle timing are not implemented in this MVP.")
  except Exception as e: st.error(f"Generation failed: {e}")
  finally: shutil.rmtree(work,ignore_errors=True)
def render(img,audio,output,music_path=None):
 ffmpeg=shutil.which("ffmpeg")
 if not ffmpeg: raise RuntimeError("FFmpeg not found. Install FFmpeg on the host.")
 cmd=[ffmpeg,"-y","-loop","1","-i",str(img),"-i",str(audio)]
 if music_path: cmd += ["-stream_loop","-1","-i",str(music_path)]
 vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0005,1.08)':d=1:s=1080x1920:fps=30,drawtext=text='Kiran Kumar • AI Automation':fontcolor=white:fontsize=36:box=1:boxcolor=0x101828AA:boxborderw=14:x=(w-text_w)/2:y=h-180"
 cmd += ["-vf",vf,"-r","30","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-shortest"]
 if music_path: cmd += ["-filter_complex","[1:a]volume=1[voice];[2:a]volume=0.08[bg];[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[a]","-map","0:v","-map","[a]"]
 cmd += ["-movflags","+faststart",str(output)]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=600)
 if p.returncode: raise RuntimeError("FFmpeg failed: "+p.stderr[-1500:])
