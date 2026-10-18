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
