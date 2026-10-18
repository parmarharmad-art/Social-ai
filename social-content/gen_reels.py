"""Generate 1080x1920 branded Instagram reels (MP4): 8 colour themes x 5 layouts, rotating photos.

usage: python gen_reels.py reels.json assets_dir out_dir [only_n]
Needs: pillow, numpy, ffmpeg on PATH. Photos: every assets/person*.png (transparent cutout) rotates.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice  # noqa: E402

VERSION = "v2-variety"
data_path, assets, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
only = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
os.makedirs(out_dir, exist_ok=True)

W, H, FPS = 1080, 1920, 30
BAND = 190
white = (255, 255, 255)

THEMES = [
    dict(name="navy", top=(8, 24, 58), bot=(16, 48, 104), glow=(60, 120, 230), acc=(255, 196, 0), txt=white, band=(6, 18, 44), pat="dots", light=False),
    dict(name="forest", top=(6, 34, 28), bot=(12, 84, 62), glow=(40, 200, 140), acc=(140, 255, 190), txt=white, band=(4, 24, 20), pat="grid", light=False),
    dict(name="ember", top=(20, 18, 22), bot=(52, 30, 24), glow=(255, 110, 40), acc=(255, 128, 48), txt=white, band=(14, 12, 14), pat="stripes", light=False),
    dict(name="violet", top=(34, 12, 66), bot=(78, 30, 118), glow=(170, 90, 255), acc=(255, 214, 102), txt=white, band=(22, 8, 44), pat="rings", light=False),
    dict(name="paper", top=(246, 242, 234), bot=(230, 224, 212), glow=(255, 190, 120), acc=(214, 64, 20), txt=(18, 24, 38), band=(18, 24, 38), pat="dots", light=True),
    dict(name="crimson", top=(58, 8, 18), bot=(124, 22, 42), glow=(255, 80, 90), acc=(255, 226, 130), txt=white, band=(36, 4, 12), pat="stripes", light=False),
    dict(name="teal", top=(4, 48, 60), bot=(8, 104, 112), glow=(60, 230, 220), acc=(255, 236, 120), txt=white, band=(2, 30, 40), pat="rings", light=False),
    dict(name="lime", top=(8, 8, 8), bot=(26, 26, 26), glow=(150, 200, 0), acc=(198, 255, 0), txt=white, band=(0, 0, 0), pat="grid", light=False),
]
LAYOUTS = ["stack", "side", "topphoto", "badge", "single"]


def find_font(names):
    for d in (os.path.join(assets, "fonts"), "/usr/share/fonts/truetype/google-fonts",
              "/usr/share/fonts/truetype/dejavu"):
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    raise SystemExit("font not found: %s" % names)


BOLD = find_font(["Poppins-Bold.ttf", "DejaVuSans-Bold.ttf"])
SEMI = find_font(["Poppins-SemiBold.ttf", "Poppins-Bold.ttf", "DejaVuSans-Bold.ttf"])


def load_poses():
    out = []
    for p in sorted(glob.glob(os.path.join(assets, "person*.png"))):
        im = Image.open(p).convert("RGBA")
        bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        if bb:
            im = im.crop(bb)
        out.append(im)
    if not out:
        raise SystemExit("no person*.png in %s" % assets)
    return out


POSES = load_poses()


def is_bust(im):
    return im.height / im.width < 1.15


def bust_crop(im, ratio=0.95):
    """top part of a photo (fades out at the bottom edge when it was cut)."""
    h = int(im.width * ratio)
    if h >= im.height:
        return im
    c = im.crop((0, 0, im.width, h)).copy()
    a = np.array(c.getchannel("A"), np.float32)
    fade = np.ones(h, np.float32)
    n = 90
    fade[-n:] = np.linspace(1, 0, n)
    c.putalpha(Image.fromarray((a * fade[:, None]).astype(np.uint8)))
    return c


def circle_badge(im, diam, ring):
    side = min(im.width, int(im.height * 0.62 if not is_bust(im) else im.height))
    x0 = (im.width - side) // 2
    sq = im.crop((x0, 0, x0 + side, side)).resize((diam, diam), Image.LANCZOS)
    out = Image.new("RGBA", (diam + 16, diam + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.ellipse((0, 0, diam + 15, diam + 15), fill=ring + (255,))
    inner = Image.new("RGBA", (diam, diam), (30, 40, 70, 255))
    inner.alpha_composite(sq)
    mask = Image.new("L", (diam, diam), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diam - 1, diam - 1), fill=255)
    out.paste(inner, (8, 8), mask)
    return out


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def background(th):
    top = np.array(th["top"], np.float32)
    bot = np.array(th["bot"], np.float32)
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    img = Image.fromarray(np.repeat(top * (1 - ys) + bot * ys, W, axis=1).astype(np.uint8), "RGB").convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((140, 1000, 1000, 1800), fill=th["glow"] + (110,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(120)))
    pat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pat)
    ink = (0, 0, 0, 22) if th["light"] else (255, 255, 255, 24)
    if th["pat"] == "dots":
        for gx in range(40, W, 60):
            for gy in range(40, H - BAND, 60):
                pd.ellipse((gx - 2, gy - 2, gx + 2, gy + 2), fill=ink)
    elif th["pat"] == "grid":
        for gx in range(0, W, 90):
            pd.line((gx, 0, gx, H - BAND), fill=ink, width=2)
        for gy in range(0, H - BAND, 90):
            pd.line((0, gy, W, gy), fill=ink, width=2)
    elif th["pat"] == "stripes":
        for k in range(-H, W, 70):
            pd.line((k, H - BAND, k + H, 0), fill=ink, width=10)
    else:
        for r in range(160, 1500, 130):
            pd.ellipse((W - r, 300 - r, W + r, 300 + r), outline=ink, width=3)
    return Image.alpha_composite(img, pat)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def text_layer(lines, font, color, lh):
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w = max(int(d0.textlength(l, font=font)) for l in lines) + 20
    layer = Image.new("RGBA", (w, lh * len(lines) + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, l in enumerate(lines):
        d.text((0, i * lh), l, font=font, fill=color)
    return layer


def paste_fade(canvas, layer, x, y, alpha, dx=0, dy=0):
    if alpha <= 0:
        return
    if alpha < 1:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer = layer.copy()
        layer.putalpha(a)
    canvas.alpha_composite(layer, (int(x + dx), int(y + dy)))


def bullet_row(i, text, th, fsize, maxw, card_w=None):
    f_b = ImageFont.truetype(SEMI, fsize)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = wrap(d0, text, f_b, maxw)
    lh = int(fsize * 1.2)
    t = text_layer(lines, f_b, th["txt"] + (255,), lh)
    pad = 22 if card_w else 0
    h = max(t.height, 72) + 2 * pad
    w = card_w or (100 + maxw + 20)
    row = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rd = ImageDraw.Draw(row)
    if card_w:
        fill = (0, 0, 0, 22) if th["light"] else (255, 255, 255, 28)
        rd.rounded_rectangle((0, 0, w - 1, h - 1), 28, fill=fill)
    cy = pad + 4
    rd.ellipse((pad, cy, pad + 68, cy + 68), fill=th["acc"] + (255,))
    nf = ImageFont.truetype(BOLD, 38)
    tw = rd.textlength(str(i), font=nf)
    ncol = (255, 255, 255) if th["light"] else (8, 18, 40)
    rd.text((pad + 34 - tw / 2, cy + 8), str(i), font=nf, fill=ncol)
    row.alpha_composite(t, (pad + 100, pad + 2))
    return row


def place_person(bg, person, x, y, shadow=True):
    if shadow:
        sh = Image.new("RGBA", person.size, (0, 0, 0, 0))
        sh.putalpha(person.getchannel("A").point(lambda v: int(v * 0.5)))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.paste(sh, (x + 8, y + 12), sh)
        bg = Image.alpha_composite(bg, layer.filter(ImageFilter.GaussianBlur(18)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(person, (x, y), person)
    return Image.alpha_composite(bg, layer)


def scale_w(im, pw):
    return im.resize((pw, int(im.height * pw / im.width)), Image.LANCZOS)


def build(item):
    n = item["n"]
    th = THEMES[(n * 3 + 1) % len(THEMES)]
    layout = LAYOUTS[(n - 1) % len(LAYOUTS)]
    pose = POSES[(n - 1) % len(POSES)]
    pts = item["pts"]
    bg = background(th)
    d = ImageDraw.Draw(bg)
    acc = th["acc"]
    items = []
    cx = lambda im: (W - im.width) // 2

    def make_head(font_size, lh, maxw=W - 120, color=None):
        f = ImageFont.truetype(BOLD, font_size)
        return text_layer(wrap(d, item["h"], f, maxw), f, (color or th["txt"]) + (255,), lh)

    if layout == "stack":
        head = make_head(104, 122)
        hy = 120
        rows = [bullet_row(i, p, th, 58, W - 260) for i, p in enumerate(pts, 1)]
        by0 = hy + head.height + 60
        bh = sum(r.height + 36 for r in rows)
        avail = (H - BAND) - (by0 + bh) + 100
        if is_bust(pose):
            pw = max(520, min(900 if len(pts) <= 4 else 760, int(avail * pose.width / pose.height)))
        else:
            pw = max(480, min(660, int(avail * pose.width / pose.height)))
        person = scale_w(pose, pw)
        bg = place_person(bg, person, (W - pw) // 2, H - BAND - person.height + 2)
        items.append((head, 60, hy, "head"))
        y = by0
        for r in rows:
            items.append((r, 60, y, "bullet"))
            y += r.height + 36
    elif layout == "side":
        head = make_head(96, 112)
        hy = 110
        rows = [bullet_row(i, p, th, 50, 380) for i, p in enumerate(pts, 1)]
        pw = 640 if is_bust(pose) else 540
        person = scale_w(pose, pw)
        bg = place_person(bg, person, W - pw + 30, H - BAND - person.height + 2)
        items.append((head, 60, hy, "head"))
        y = hy + head.height + 50
        for r in rows:
            items.append((r, 50, y, "bullet"))
            y += r.height + 30
    elif layout == "topphoto":
        top = bust_crop(pose, 0.95) if not is_bust(pose) else pose
        person = scale_w(top, 700)
        bg = place_person(bg, person, (W - 700) // 2, 60)
        head = make_head(92, 108)
        hy = 60 + person.height + 10
        rows = [bullet_row(i, p, th, 54, W - 260) for i, p in enumerate(pts, 1)]
        items.append((head, 60, hy, "head"))
        y = hy + head.height + 40
        for r in rows:
            items.append((r, 60, y, "bullet"))
            y += r.height + 30
    elif layout == "badge":
        badge = circle_badge(pose, 280, acc)
        bg.alpha_composite(badge, (60, 110))
        d = ImageDraw.Draw(bg)
        d.text((400, 160), "KIRAN KUMAR", font=ImageFont.truetype(BOLD, 62), fill=th["txt"])
        d.text((400, 240), "AI AUTOMATION EXPERT", font=ImageFont.truetype(SEMI, 32), fill=acc)
        d.rectangle((400, 296, 520, 304), fill=acc)
        head = make_head(100, 118)
        hy = 470
        rows = [bullet_row(i, p, th, 52, W - 300, card_w=W - 120) for i, p in enumerate(pts, 1)]
        items.append((head, 60, hy, "head"))
        y = hy + head.height + 40
        for r in rows:
            items.append((r, 60, y, "bullet"))
            y += r.height + 22
    else:
        pw = 560 if is_bust(pose) else 470
        person = scale_w(pose, pw)
        bg = place_person(bg, person, W - pw + 20, H - BAND - person.height + 2)
        head = make_head(80, 96, color=acc)
        hy = 120
        items.append((head, 60, hy, "head"))
        f_big = ImageFont.truetype(BOLD, 84)
        for i, p in enumerate(pts, 1):
            lines = wrap(d, p, f_big, W - 140)
            t = text_layer(lines, f_big, th["txt"] + (255,), 100)
            row = Image.new("RGBA", (W - 120, t.height + 170), (0, 0, 0, 0))
            rd = ImageDraw.Draw(row)
            rd.ellipse((0, 0, 120, 120), fill=acc + (255,))
            nf = ImageFont.truetype(BOLD, 72)
            tw = rd.textlength(str(i), font=nf)
            rd.text((60 - tw / 2, 14), str(i), font=nf, fill=(255, 255, 255) if th["light"] else (8, 18, 40))
            row.alpha_composite(t, (0, 150))
            items.append((row, 60, hy + head.height + 90, "single"))

    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    fade = np.zeros((50, W, 4), np.uint8)
    fade[..., 0:3] = th["band"]
    fade[..., 3] = np.linspace(0, 255, 50, dtype=np.uint8)[:, None]
    band.paste(Image.fromarray(fade, "RGBA"), (0, H - BAND - 50))
    bd.rectangle((0, H - BAND, W, H), fill=th["band"] + (255,))
    bd.rectangle((0, H - BAND, W, H - BAND + 6), fill=acc + (255,))
    bg = Image.alpha_composite(bg, band)
    d = ImageDraw.Draw(bg)
    d.text((60, H - BAND + 36), "KIRAN KUMAR", font=ImageFont.truetype(BOLD, 62), fill=white)
    d.text((60, H - BAND + 112), "AI AUTOMATION EXPERT", font=ImageFont.truetype(SEMI, 32), fill=acc)

    f_c = ImageFont.truetype(BOLD, 50)
    cta_text = item.get("cta", "Follow @officialkiraankumar")
    cta_w = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(cta_text, font=f_c)) + 90
    cta = Image.new("RGBA", (cta_w, 100), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cta)
    cd.rounded_rectangle((0, 0, cta_w - 1, 99), 50, fill=acc + (255,))
    cd.text((45, 18), cta_text, font=f_c, fill=(255, 255, 255) if th["light"] else (8, 18, 40))
    return bg, items, cta, layout, th, acc


SR = 44100


def pcm(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1",
                          "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def music(n_samples):
    t = np.arange(n_samples, dtype=np.float32) / SR
    chord = sum(np.sin(2 * np.pi * f * t) for f in (110.0, 164.81, 220.0, 277.18))
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 8.0)
    return (chord * swell * 0.035).astype(np.float32)


def plan_audio(item, tmp):
    if os.environ.get("NO_VOICE") == "1":
        return None
    texts = [item["h"]] + item["pts"] + [item.get("voice_cta", "Follow Kiran Kumar for daily AI automation tips.")]
    clips = []
    for i, tx in enumerate(texts):
        p = os.path.join(tmp, "s%d.mp3" % i)
        if not voice.synth(tx, p):
            return None
        clips.append(pcm(p))
    t = 0.5
    starts = []
    gap = 0.45
    for c in clips:
        starts.append(t)
        t += len(c) / SR + gap
    dur = max(t + 0.9, 10.0)
    buf = music(int(dur * SR))
    for st, c in zip(starts, clips):
        a = int(st * SR)
        buf[a:a + len(c)] += c * 0.9
    buf = np.clip(buf, -1, 1)
    wav = os.path.join(tmp, "mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    return starts, dur, wav


def render(item):
    bg, items, cta, layout, th, acc = build(item)
    tmp = tempfile.mkdtemp()
    plan = plan_audio(item, tmp)
    npts = len(item["pts"])
    if plan:
        starts, dur, wav = plan
        bullet_t = [s - 0.1 for s in starts[1:1 + npts]]
        cta_start = starts[-1] - 0.1
        audio_in = ["-i", wav]
    else:
        dur = item.get("dur", 6 + 2.4 * npts)
        bullet_t = [1.2 + i * 2.2 for i in range(npts)]
        cta_start = dur - 2.6
        audio_in = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    total = int(dur * FPS)
    out = os.path.join(out_dir, "%02d.mp4" % item["n"])
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-"] + audio_in + [
           "-t", "%.2f" % dur, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
           "-crf", "22", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    bullets = [it for it in items if it[3] in ("bullet", "single")]
    for f in range(total):
        t = f / FPS
        frame = bg.copy()
        a = ease(t / 0.7)
        hl, hx, hy, _ = items[0]
        if layout == "side":
            paste_fade(frame, hl, hx, hy, a, dx=(1 - a) * -120)
        else:
            paste_fade(frame, hl, hx, hy, a, dy=(1 - a) * 60)
        for i, (layer, x, y, kind) in enumerate(bullets):
            a = ease((t - bullet_t[i]) / 0.6)
            if kind == "single":
                if i + 1 < len(bullets) and t >= bullet_t[i + 1]:
                    continue
                paste_fade(frame, layer, x, y, a, dx=(1 - a) * 160)
            elif layout == "side":
                paste_fade(frame, layer, x, y, a, dx=(1 - a) * -160)
            else:
                paste_fade(frame, layer, x, y, a, dy=(1 - a) * 50)
        if layout == "single":
            d = ImageDraw.Draw(frame)
            cur = max([i for i in range(npts) if t >= bullet_t[i]] or [-1])
            for i in range(npts):
                d.ellipse((60 + i * 44, H - BAND - 34, 60 + i * 44 + 26, H - BAND - 10),
                          fill=acc + (255,) if i == cur else acc + (70,))
        if t >= cta_start:
            a = ease((t - cta_start) / 0.5)
            paste_fade(frame, cta, (W - cta.width) // 2, H - BAND - 150, a, dy=(1 - a) * 40)
        d = ImageDraw.Draw(frame)
        d.rectangle((0, 0, int(W * t / dur), 10), fill=acc + (255,))
        p.stdin.write(np.asarray(frame.convert("RGB")).tobytes())
    p.stdin.close()
    p.wait()
    print("wrote", out, th["name"], layout, "voice" if plan else "silent", "%.1fs" % dur)


ver_file = os.path.join(out_dir, ".ver")
same_ver = os.path.exists(ver_file) and open(ver_file).read().strip() == VERSION
for item in json.load(open(data_path)):
    if only and item["n"] != only:
        continue
    if same_ver and os.environ.get("SKIP_EXISTING") == "1" and os.path.exists(os.path.join(out_dir, "%02d.mp4" % item["n"])):
        continue
    render(item)
if not only:
    open(ver_file, "w").write(VERSION)
