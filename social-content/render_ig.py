import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

data_path, person_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out_dir, exist_ok=True)
W, H = 1080, 1350
BAND = 130
yellow = (255, 196, 0)
fdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
bold = os.path.join(fdir, "Poppins-Bold.ttf")
semi = os.path.join(fdir, "Poppins-SemiBold.ttf")
if not os.path.exists(semi):
    semi = bold
reg = os.path.join(fdir, "Poppins-Medium.ttf")
if not os.path.exists(reg):
    reg = semi

person_a = Image.open(person_path).convert("RGBA")
person_a = person_a.crop((0, 0, person_a.width, 664))
person_b = Image.open(os.path.join(os.path.dirname(person_path), "person_b.png")).convert("RGBA")


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


def background():
    top = np.array([8, 24, 58], np.float32)
    bot = np.array([16, 48, 104], np.float32)
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    grad = top * (1 - ys) + bot * ys
    img = Image.fromarray(np.repeat(grad, W, axis=1).astype(np.uint8), "RGB").convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((330, 560, 1130, 1260), fill=(60, 120, 230, 120))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(110)))
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for gx in range(40, W, 54):
        for gy in range(40, H - BAND, 54):
            dd.ellipse((gx - 2, gy - 2, gx + 2, gy + 2), fill=(255, 255, 255, 24))
    return Image.alpha_composite(img, dots)


for item in json.load(open(data_path)):
    canvas = background()
    d = ImageDraw.Draw(canvas)

    # person bottom-right
    if item["n"] % 2 == 1:
        person_src, pw, dx = person_a, 700, 20
    else:
        person_src, pw, dx = person_b, 600, 10
    ph = int(person_src.height * pw / person_src.width)
    person = person_src.resize((pw, ph), Image.LANCZOS)
    px, py = W - pw + dx, H - BAND - ph + 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", person.size, (0, 0, 0, 0))
    sh.putalpha(person.getchannel("A").point(lambda v: int(v * 0.5)))
    shadow.paste(sh, (px + 8, py + 12), sh)
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(16)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(person, (px, py), person)
    canvas = Image.alpha_composite(canvas, layer)
    d = ImageDraw.Draw(canvas)

    # headline
    f_h = ImageFont.truetype(bold, 84)
    lines = wrap(d, item["h"], f_h, W - 120)
    y = 70
    d.rectangle((60, y - 6, 60 + 90, y + 4), fill=yellow)
    y += 24
    for ln in lines:
        d.text((60, y), ln, font=f_h, fill=(255, 255, 255))
        y += 100

    # bullets (left column)
    f_b = ImageFont.truetype(semi, 46)
    y += 30
    maxw = 500
    for i, p in enumerate(item["pts"], 1):
        bl = wrap(d, p, f_b, maxw)
        d.ellipse((60, y + 4, 112, y + 56), fill=yellow)
        nf = ImageFont.truetype(bold, 28)
        tw = d.textlength(str(i), font=nf)
        d.text((84 - tw / 2, y + 5), str(i), font=nf, fill=(8, 24, 58))
        ty = y + 2
        for b in bl:
            d.text((134, ty), b, font=f_b, fill=(255, 255, 255))
            ty += 58
        y = max(y + 84, ty + 30)

    # bottom band
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    fade_h = 40
    fade = np.zeros((fade_h, W, 4), np.uint8)
    fade[..., 0:3] = (6, 18, 44)
    fade[..., 3] = np.linspace(0, 255, fade_h, dtype=np.uint8)[:, None]
    band.paste(Image.fromarray(fade, "RGBA"), (0, H - BAND - fade_h))
    bd.rectangle((0, H - BAND, W, H), fill=(6, 18, 44, 255))
    bd.rectangle((0, H - BAND, W, H - BAND + 5), fill=yellow + (255,))
    canvas = Image.alpha_composite(canvas, band)
    d = ImageDraw.Draw(canvas)
    d.text((60, H - BAND + 22), "KIRAN KUMAR", font=ImageFont.truetype(bold, 46), fill=(255, 255, 255))
    d.text((60, H - BAND + 78), "AI AUTOMATION EXPERT", font=ImageFont.truetype(semi, 26), fill=yellow)
    d.text((W - 60 - d.textlength("SAVE THIS POST", font=ImageFont.truetype(bold, 28)), H - BAND + 48),
           "SAVE THIS POST", font=ImageFont.truetype(bold, 28), fill=yellow)

    out = os.path.join(out_dir, f"{item['n']:02d}.jpg")
    canvas.convert("RGB").save(out, quality=90, optimize=True)
print("ok")
