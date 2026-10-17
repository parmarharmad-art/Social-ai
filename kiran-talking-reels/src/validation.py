from pathlib import Path
import json,subprocess,shutil
from PIL import Image
def validate_image(path):
 p=Path(path)
 if not p.exists() or p.stat().st_size==0: raise ValueError("Image missing or empty.")
 try:
  with Image.open(p) as im: im.verify()
 except Exception as e: raise ValueError("Invalid or unsupported image.") from e
def ffprobe_info(path):
 probe=shutil.which("ffprobe")
 if not probe: return {"note":"ffprobe unavailable; only file existence was checked"}
 p=subprocess.run([probe,"-v","error","-show_entries","format=duration,format_name","-show_entries","stream=codec_name,width,height","-of","json",str(path)],capture_output=True,text=True,timeout=30)
 if p.returncode: raise RuntimeError("ffprobe validation failed: "+p.stderr[-400:])
 data=json.loads(p.stdout)
 videos=[s for s in data.get("streams",[]) if "width" in s]
 if not videos or videos[0].get("width")!=1080 or videos[0].get("height")!=1920: raise ValueError("Expected 1080x1920 video.")
 return data
