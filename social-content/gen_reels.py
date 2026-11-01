#!/usr/bin/env python3
"""v3 animated Reel renderer: normal reels + BOOK_MODE, Hindi voice, karaoke captions."""
import glob, json, os, subprocess, sys, tempfile, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice

VERSION = "v3-animated"
W,H,FPS,SR = 1080,1920,24,44100
THEMES = {
 "navy":((7,16,38),(20,48,82),(58,210,255)),
 "violet":((24,12,48),(67,35,112),(190,130,255)),
 "ember":((43,16,12),(112,42,24),(255,166,75)),
 "forest":((7, thirty:=24, 27),(20,75,57),(106,230,164)),
 "crimson":((38,9,24),(105,25,49),(255,105,140)),
 "indigo":((12,17,54),(37,47,116),(133,160,255)),
}
if len(sys.argv)<4: raise SystemExit("Usage: gen_reels.py reels.json assets_dir out_dir [only_n]")
DATA,ASSETS,OUT=sys.argv[1:4]
ONLY=int(sys.argv[4]) if len(sys.argv)>4 and sys.argv[4].isdigit() else None
BOOK_MODE=os.getenv("BOOK_MODE")=="1"
os.makedirs(OUT,exist_ok=True)
FONT_CANDIDATES=[os.path.join(ASSETS,"fonts","NotoSansDevanagari-Bold.ttf"),"/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FONT=next((p for p in FONT_CANDIDATES if os.path.isfile(p)),None)
if not FONT: raise SystemExit("Noto/DejaVu font missing")
def ft(size): return ImageFont.truetype(FONT,size)
def fit(draw,s,maxw,size=60):
 while size>28 and draw.textbbox((0,0),str(s),font=ft(size))[2]>maxw: size-=2
 return ft(size)
def wrap(draw,s,font,width):
 out=[]; line=""
 for word in str(s).split():
  test=(line+" "+word).strip()
  if draw.textbbox((0,0),test,font=font)[2]<=width: line=test
 else:
  if line: out.append(line)
  return out or [""]
def theme_for(item):
 key=str(item.get("theme","navy")).lower()
 return THEMES.get(key,THEMES[list(THEMES)[int(item.get("n",item.get("id",1)))%len(THEMES)]])
def bg(item):
 top,bottom,accent=theme_for(item)
 a=np.zeros((H,W,3),dtype=np.uint8)
 for y in range(H):
  t=y/(H-1); a[y,:,:]=(np.array(top)*(1-t)+np.array(bottom)*t).astype("uint8")
 im=Image.fromarray(a,"RGB").convert("RGBA")
 glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
 gd.ellipse((650,900,1320,1580),fill=(*accent,70))
 return Image.alpha_composite(im,glow.filter(ImageFilter.GaussianBlur(120)))
def cover_for(n):
 for p in [os.path.join(ASSETS,f"book_{n:02d}.png"),os.path.join(ASSETS,f"book_{n}.png")]:
  if os.path.isfile(p): return Image.open(p).convert("RGBA")
 pool=sorted(glob.glob(os.path.join(ASSETS,"book_*.png")))
 return Image.open(pool[(n-1)%len(pool)]).convert("RGBA") if pool else None
def draw_center(d,text,y,font,fill,anchor="mm"):
 d.text((W//2,y),text,font=font,fill=fill,anchor=anchor)
def make_frame(item,headline,caption,highlight=None,idx=0,total=1):
 top,bottom,accent=theme_for(item); im=bg(item); d=ImageDraw.Draw(im)
 d.rounded_rectangle((55,55,1025,145),radius=30,fill=(255,255,255,18),outline=(*accent,170),width=2)
 d.text((88,82),"KIRAN KUMAR  •  AI INSIGHTS",font=ft(30),fill=(*accent,255))
 if BOOK_MODE and idx==0:
  cover=cover_for(int(item.get("n",item.get("id",1))))
  if cover:
   cover.thumbnail((490,620),Image.Resampling.LANCZOS)
   im.alpha_composite(cover,((W-cover.width)//2,205))
  else:
   d.rounded_rectangle((240,210,840,850),radius=36,fill=(*top,255),outline=(*accent,255),width=5)
   for j,line in enumerate(wrap(d,item.get("book","BOOK INSIGHT"),fit(d,item.get("book","BOOK INSIGHT"),500,56),500)):
    draw_center(d,line,480+j*75,fit(d,line,500,56),(255,255,255,255))
  title=item.get("book",headline)
  for j,line in enumerate(wrap(d,title,fit(d,title,900,48),900)[:2]): draw_center(d,line,950+j*60,fit(d,line,900,48),(255,255,255,255))
  draw_center(d,item.get("author",""),1080,ft(32),(*accent,255))
 else:
  for j,line in enumerate(wrap(d,headline,fit(d,headline,900,70),900)[:4]): draw_center(d,line,440+j*88,fit(d,line,900,70),(255,255,255,255))
 if caption:
  words=caption.split(); d.rounded_rectangle((70,1120,1010,1510),radius=34,fill=(0,0,0,210),outline=(*accent,210),width=3)
  shown=words if highlight is None else words[:highlight+1]
  # Word-by-word karaoke: active word is accent-colored.
  full=" ".join(shown); f=fit(d,full,850,44)
  lines=wrap(d,full,f,850)
  for j,line in enumerate(lines[:4]): draw_center(d,line,1210+j*72,f,(255,255,255,255))
  if highlight is not None and words:
   active=words[min(highlight,len(words)-1)]
   draw_center(d,"▶ "+active,1460,fit(d,active,700,38),(*accent,255))
 d.rounded_rectangle((70,1580,1010,1810),radius=34,fill=(3,10,25,235),outline=(*accent,180),width=2)
 cta=item.get("cta","Save karo aur follow @officialkiraankumar")
 draw_center(d,cta,1660,fit(d,cta,850,42),(255,205,100,255))
 draw_center(d,"@officialkiraankumar",1740,ft(30),(255,255,255,255))
 return im.convert("RGB")
def make_audio(lines,tmp):
 clips=[]; starts=[]; cursor=.35
 for i,line in enumerate(lines):
  p=os.path.join(tmp,f"voice_{i:02d}.mp3")
  if not voice.synth(line,p): raise RuntimeError(f"Voice generation failed at segment {i+1}; refusing silent render")
  raw=subprocess.run(["ffmpeg","-v","error","-i",p,"-f","s16le","-ac","1","-ar",str(SR),"-"],check=True,capture_output=True).stdout
  samples=np.frombuffer(raw,dtype=np.int16).astype(np.float32)/32768
  clips.append(samples); starts.append(cursor); cursor+=len(samples)/SR+.32
 dur=cursor+.6; mix=np.zeros(int(dur*SR),dtype=np.float32)
 t=np.arange(len(mix))/SR
 bed=(np.sin(2*np.pi*110*t)+.4*np.sin(2*np.pi*165*t))*.009
 mix+=bed.astype(np.float32)
 for start,s in zip(starts,clips):
  pos=int(start*SR); mix[pos:pos+len(s)]+=s*.78
 peak=max(float(np.max(np.abs(mix))),.01); mix=np.clip(mix*min(1,.92/peak),-.98,.98)
 wavp=os.path.join(tmp,"mix.wav")
 with wave.open(wavp,"wb") as w:
  w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix*32767).astype(np.int16).tobytes())
 return wavp,dur,starts,[len(s)/SR for s in clips]
def render(item):
 n=int(item.get("n",item.get("id",1)))
 narration=item.get("voiceover") or ([item.get("h",item.get("hook","Aaj ka lesson"))]+item.get("pts",[]))
 narration=[str(x).strip() for x in narration if str(x).strip()]
 if not narration: raise ValueError(f"No narration for reel {n}")
 tmp=tempfile.mkdtemp(prefix="reel_v3_")
 wav,duration,starts,lengths=make_audio(narration,tmp)
 frames=[]; durations=[]
 # Intro title and scene narration, with four progressive karaoke states per spoken line.
 frames.append(make_frame(item,item.get("h",item.get("hook",narration[0])),narration[0],0,0,len(narration)))
 durations.append(min(1.6,max(.9,duration*.10)))
 for i,line in enumerate(narration):
  words=line.split(); count=min(len(words),8)
  segdur=lengths[i]/max(1,count)
  for k in range(count):
   frames.append(make_frame(item,line,line,min(len(words)-1,int((k+1)*len(words)/count)-1),i+1,len(narration)))
   durations.append(max(.25,segdur))
 concat=os.path.join(tmp,"frames.txt")
 with open(concat,"w",encoding="utf-8") as f:
  for i,(im,sec) in enumerate(zip(frames,durations)):
   p=os.path.join(tmp,f"f{i:04d}.jpg"); im.save(p,quality=88)
   f.write(f"file '{p}'\nduration {sec:.3f}\n")
  f.write(f"file '{os.path.join(tmp,f'f{len(frames)-1:04d}.jpg')}'\n")
 out=os.path.join(OUT,f"{n:02d}.mp4")
 cmd=["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",concat,"-i",wav,"-vf",f"fps={FPS},scale={W}:{H},format=yuv420p","-t",f"{duration:.2f}","-r",str(FPS),"-c:v","libx264","-preset","veryfast","-crf","22","-c:a","aac","-b:a","160k","-af","loudnorm=I=-14:TP=-1.5:LRA=11","-shortest","-movflags","+faststart",out]
 subprocess.run(cmd,check=True,timeout=900)
 print(f"Rendered {out} ({duration:.1f}s) [{VERSION}]")
def main():
 with open(DATA,encoding="utf-8") as f: records=json.load(f)
 if isinstance(records,dict): records=records.get("reels",records.get("books",records.get("items",[])))
 if not isinstance(records,list) or not records: raise SystemExit("Input JSON must contain a non-empty list")
 for item in records:
  n=int(item.get("n",item.get("id",0)))
  if ONLY is None or n==ONLY: render(item)
 Path(OUT,".ver").write_text(VERSION+"\n",encoding="utf-8")
if __name__=="__main__": main()
