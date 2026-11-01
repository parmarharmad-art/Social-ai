"""Render one original screen-demo tutorial Reel with presenter PiP and animated UI.
Usage: python tutorial_reel.py reels.json assets out_dir [reel_number]
Requires Pillow, numpy, ffmpeg and the repository voice.py dependencies.
"""
import json, os, sys, subprocess, tempfile, wave, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice

W, H, FPS, SR = 1080, 1920, 24, 44100
BG = (7, 15, 34)
PANEL = (16, 29, 56)
CYAN = (62, 220, 255)
WHITE = (246, 249, 255)
MUTED = (163, 180, 207)
ACCENT = (151, 112, 255)

def font(size, bold=True):
    # Resolve the installed Hindi font through fontconfig, then require RAQM shaping.
    # Falling back silently to DejaVu produces unreadable square glyphs for Devanagari.
    pattern = "Noto Sans Devanagari:style=Bold:lang=hi" if bold else "Noto Sans Devanagari:style=Regular:lang=hi"
    try:
        path = subprocess.check_output(
            ["fc-match", "-f", "%{file}", pattern], text=True
        ).strip()
    except Exception as exc:
        raise RuntimeError("Hindi font lookup failed; install fonts-noto-core") from exc
    if not path or not os.path.isfile(path):
        raise RuntimeError("Noto Sans Devanagari font file not found")
    layout = getattr(ImageFont, "Layout", None)
    if not layout or not hasattr(layout, "RAQM"):
        raise RuntimeError("Pillow RAQM is required for correct Hindi shaping")
    try:
        return ImageFont.truetype(path, size, layout_engine=layout.RAQM)
    except Exception as exc:
        raise RuntimeError(f"Could not load Hindi font with RAQM: {path}") from exc

def rounded(draw, xy, radius, fill, outline=None, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def fit_lines(draw, text, f, maxw):
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=f) <= maxw: line = trial
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines or [text]

def draw_text(draw, xy, text, f, fill, maxw=None, spacing=12):
    x,y=xy
    lines=fit_lines(draw,text,f,maxw) if maxw else [text]
    for line in lines:
        draw.text((x,y),line,font=f,fill=fill,stroke_width=0)
        y += f.size + spacing
    return y

def make_frame(item, person, t, duration, segments):
    im=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(im)
    # Ambient glow and top brand strip
    d.ellipse((620,80,1280,760),fill=(13,35,68))
    d.text((58,58),"KIRAN KUMAR  /  AI AUTOMATION",font=font(30),fill=CYAN)
    d.line((58,112,1022,112),fill=(42,72,112),width=3)
    hook=item["h"]
    # Opening hook / scene 0: presenter full-frame cutout with hook panel
    scene=min(4,int(t/duration*5))
    if scene == 0:
        rounded(d,(52,210,1028,780),38,PANEL,outline=(49,91,142),width=3)
        draw_text(d,(95,275),hook,font(66),WHITE,890,18)
        d.text((96,680),"LET'S BUILD IT",font=font(34),fill=CYAN)
        p=person.copy(); p.thumbnail((590,880),Image.Resampling.LANCZOS)
        im.paste(p,(W-p.width-20,H-p.height-170),p if p.mode=="RGBA" else None)
    else:
        # Screen demo workspace
        rounded(d,(42,190,1038,1450),36,(11,22,44),outline=(48,78,122),width=3)
        rounded(d,(42,190,1038,290),36,(22,38,68))
        d.ellipse((78,228,100,250),fill=(255,105,110)); d.ellipse((116,228,138,250),fill=(255,205,92)); d.ellipse((154,228,176,250),fill=(93,220,157))
        d.text((215,220),"WORKFLOW STUDIO  •  LIVE PREVIEW",font=font(29),fill=WHITE)
        # Fake document / prompt UI with typing animation
        rounded(d,(86,340,994,560),24,(22,37,65),outline=(54,88,133))
        d.text((122,378),"INPUT / TASK",font=font(25),fill=CYAN)
        prompt="Turn this repetitive task into a clear workflow"
        chars=min(len(prompt),max(0,int((t%duration)*2.7)))
        d.text((122,438),prompt[:chars],font=font(31),fill=WHITE)
        d.rectangle((122+int(d.textlength(prompt[:chars],font=font(31))),443,122+int(d.textlength(prompt[:chars],font=font(31)))+4,485),fill=CYAN)
        # Four process cards, active card changes with scene
        labels=["TRIGGER","PROCESS","REVIEW","RESULT"]
        desc=["New enquiry received","Capture details + classify","Human checks the draft","Owner gets clear next step"]
        active=min(3,scene-1)
        for i,(lab,txt) in enumerate(zip(labels,desc)):
            y=650+i*168
            col=CYAN if i==active else (59,83,119)
            rounded(d,(90,y,990,y+128),22,(19,34,60),outline=col,width=4 if i==active else 2)
            d.ellipse((120,y+34,180,y+94),fill=col)
            d.text((139,y+42),str(i+1),font=font(30),fill=BG)
            d.text((210,y+22),lab,font=font(25),fill=col)
            d.text((210,y+62),txt,font=font(29),fill=WHITE)
            if i<3: d.line((150,y+130,150,y+158),fill=(87,117,157),width=5)
        # Presenter PiP bubble
        p=person.copy()
        p.thumbnail((250,330),Image.Resampling.LANCZOS)
        circle=Image.new("RGBA",(250,250),(0,0,0,0))
        crop=p.crop((0,0,min(p.width,250),min(p.height,250))).resize((226,226))
        mask=Image.new("L",(226,226),0); ImageDraw.Draw(mask).ellipse((0,0,225,225),fill=255)
        circle.paste(crop,(12,12),mask)
        cd=ImageDraw.Draw(circle); cd.ellipse((5,5,245,245),outline=CYAN,width=8)
        im.paste(circle,(W-290,1220),circle)
    # Captions and lower progress bar
    seg=segments[min(len(segments)-1,int(t/duration*len(segments)))]
    rounded(d,(52,1510,1028,1740),28,(20,34,61),outline=(51,84,128),width=2)
    draw_text(d,(92,1570),seg,font(43),WHITE,890,12)
    d.rectangle((52,1810,1028,1822),fill=(36,53,80))
    d.rectangle((52,1810,52+int(976*min(1,t/duration)),1822),fill=CYAN)
    d.text((58,1850),"@officialkiraankumar",font=font(30),fill=MUTED)
    return im

def main():
    if len(sys.argv)<4: raise SystemExit("usage: tutorial_reel.py reels.json assets out_dir [reel_number]")
    data=json.load(open(sys.argv[1],encoding="utf-8")); assets=sys.argv[2]; outdir=sys.argv[3]
    target=int(sys.argv[4]) if len(sys.argv)>4 else 1
    item=next((x for x in data if int(x["n"])==target),None)
    if not item: raise SystemExit("Reel number not found")
    os.makedirs(outdir,exist_ok=True)
    photo=Image.open(os.path.join(assets,"person_rgba.png")).convert("RGBA")
    alpha=photo.getchannel("A")
    box=alpha.getbbox()
    if box: photo=photo.crop(box)
    narration=" ".join([item["h"]]+item["pts"]+[item.get("voice_cta","Follow Kiran Kumar for more practical AI automation tutorials.")])
    segments=[item["h"]]+item["pts"]+[item.get("voice_cta","Follow Kiran Kumar for more practical AI automation tutorials.")]
    tmp=tempfile.mkdtemp(prefix="tutorial-reel-")
    mp3=os.path.join(tmp,"voice.mp3")
    if not voice.synth(narration,mp3): raise SystemExit("Voice generation failed; no silent Reel created.")
    pcm=subprocess.run(["ffmpeg","-v","error","-i",mp3,"-f","s16le","-ac","1","-ar",str(SR),"-"],check=True,capture_output=True).stdout
    audio=np.frombuffer(pcm,dtype=np.int16)
    duration=len(audio)/SR
    wav=os.path.join(tmp,"voice.wav")
    with wave.open(wav,"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(audio.tobytes())
    out=os.path.join(outdir,"%02d-tutorial.mp4"%target)
    cmd=["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-i",wav,"-t",f"{duration:.2f}","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",out]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    total=int(duration*FPS)
    for frame_no in range(total):
        t=frame_no/FPS
        frame=make_frame(item,photo,t,duration,segments)
        proc.stdin.write(np.asarray(frame,dtype=np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait()!=0: raise SystemExit("ffmpeg encoding failed")
    print(f"CREATED {out} duration={duration:.1f}s resolution={W}x{H} fps={FPS}")
if __name__=="__main__": main()
