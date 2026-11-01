"""Instagram card and carousel renderer.
Usage: python render_ig.py ig.json assets/person_rgba.png out_dir
Photo assets are optional while SHOW_PHOTO is False.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

data_path, person_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out_dir, exist_ok=True)
W, H, BAND = 1080, 1350, 130
HERE = os.path.dirname(os.path.abspath(__file__))
fdir = os.path.join(HERE, "assets", "fonts")
bold = os.path.join(fdir, "Poppins-Bold.ttf")
semi = os.path.join(fdir, "Poppins-SemiBold.ttf")
if not os.path.exists(semi): semi = bold
if not os.path.isfile(bold):
    raise FileNotFoundError(f"Required font not found: {bold}")
F = lambda p, s: ImageFont.truetype(p, s)
SHOW_PHOTO = False   # Set True only when both portrait assets are available

# (top, bottom, accent, glow, dark text on accent)
THEMES = [
    ((8, 24, 58), (16, 48, 104), (255, 196, 0), (60, 120, 230)),
    ((34, 12, 64), (70, 24, 120), (0, 214, 200), (150, 70, 255)),
    ((24, 24, 28), (52, 40, 36), (255, 120, 40), (255, 140, 60)),
    ((6, 44, 46), (10, 84, 80), (190, 240, 70), (30, 190, 170)),
    ((60, 12, 24), (110, 24, 40), (255, 205, 110), (230, 60, 90)),
    ((22, 20, 74), (48, 40, 140), (255, 120, 180), (110, 100, 255)),
]
pa = pb = None
if SHOW_PHOTO:
    if not os.path.isfile(person_path):
        raise FileNotFoundError(f"Portrait image not found: {person_path}")
    person_b_path = os.path.join(os.path.dirname(person_path), "person_b.png")
    if not os.path.isfile(person_b_path):
        raise FileNotFoundError(f"Second portrait image not found: {person_b_path}")
    pa = Image.open(person_path).convert("RGBA")
    pa = pa.crop((0, 0, pa.width, min(pa.height, 664)))
    pb = Image.open(person_b_path).convert("RGBA")

def wrap(d, text, font, mw):
    out, cur = [], ""
    for w in str(text).split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= mw:
            cur = t
        else:
            if cur:
                out.append(cur)
            # Keep an unusually long token intact instead of emitting a blank line.
            cur = w
    if cur:
        out.append(cur)
    return out

def fit(d, text, path, start, mw, maxlines, minsize=40):
    s = start
    while s > minsize and len(wrap(d, text, F(path, s), mw)) > maxlines:
        s -= 4
    s = max(minsize, s)
    font = F(path, s)
    return font, wrap(d, text, font, mw)

def background(th, variant):
    top, bot, acc, glow = th
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    g = np.array(top, np.float32) * (1 - ys) + np.array(bot, np.float32) * ys
    img = Image.fromarray(np.repeat(g, W, 1).astype(np.uint8), "RGB").convert("RGBA")
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    box = [(330, 560, 1130, 1260), (-150, 500, 650, 1250), (200, 100, 1000, 800), (500, -150, 1300, 500)][variant % 4]
    gd.ellipse(box, fill=glow + (120,))
    img = Image.alpha_composite(img, gl.filter(ImageFilter.GaussianBlur(110)))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    if variant % 3 == 0:    # dots
        for x in range(40, W, 54):
            for y in range(40, H - BAND, 54): od.ellipse((x-2, y-2, x+2, y+2), fill=(255, 255, 255, 24))
    elif variant % 3 == 1:  # diagonal lines
        for k in range(-H, W, 90): od.line((k, 0, k + H, H), fill=(255, 255, 255, 14), width=3)
    else:                   # rings
        for r in (260, 400, 540): od.ellipse((W-r, 80-r, W+r, 80+r), outline=(255, 255, 255, 22), width=3)
    return Image.alpha_composite(img, ov)

def paste_person(canvas, src, pw, x, bottom, flip=False):
    ph = int(src.height * pw / src.width)
    p = src.resize((pw, ph), Image.LANCZOS)
    if flip: p = p.transpose(Image.FLIP_LEFT_RIGHT)
    sh = Image.new("RGBA", p.size, (0, 0, 0, 0)); sh.putalpha(p.getchannel("A").point(lambda v: int(v * .5)))
    s = Image.new("RGBA", (W, H), (0, 0, 0, 0)); s.paste(sh, (x + 8, bottom - ph + 12), sh)
    canvas = Image.alpha_composite(canvas, s.filter(ImageFilter.GaussianBlur(16)))
    l = Image.new("RGBA", (W, H), (0, 0, 0, 0)); l.paste(p, (x, bottom - ph), p)
    return Image.alpha_composite(canvas, l)

def badge(src, s, acc):
    S = 4
    cw = src.width if src.width == src.height or src.width > src.height * 0.95 else int(src.width * 0.72)
    x0 = (src.width - cw) // 2
    face = src.convert("RGB").crop((x0, 0, x0 + cw, cw)).resize((s*S, s*S), Image.LANCZOS)
    ring = Image.new("RGBA", ((s+10)*S, (s+10)*S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, (s+10)*S-1, (s+10)*S-1), fill=acc + (255,))
    m = Image.new("L", (s*S, s*S), 0); ImageDraw.Draw(m).ellipse((0, 0, s*S-1, s*S-1), fill=255)
    ring.paste(face, (5*S, 5*S), m)
    return ring.resize((s+10, s+10), Image.LANCZOS)

def band(canvas, th, right_text, face=None):
    top, bot, acc, _ = th
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, H-BAND, W, H), fill=(6, 14, 34)); d.rectangle((0, H-BAND, W, H-BAND+5), fill=acc)
    x = 60
    if face is not None:
        canvas.paste(face, (50, H-BAND+(BAND-face.height)//2+2), face); x = 50 + face.width + 24
    d.text((x, H-BAND+22), "KIRAN KUMAR", font=F(bold, 44), fill=(255, 255, 255))
    d.text((x, H-BAND+76), "AI AUTOMATION EXPERT", font=F(semi, 25), fill=acc)
    rf = F(bold, 28); d.text((W-60-d.textlength(right_text, font=rf), H-BAND+48), right_text, font=rf, fill=acc)

def headline(d, item, th, x, y, mw, size=84, maxlines=3):
    acc = th[2]
    d.rectangle((x, y-6, x+90, y+4), fill=acc); y += 24
    f, lines = fit(d, item["h"], bold, size, mw, maxlines)
    for ln in lines:
        d.text((x, y), ln, font=f, fill=(255, 255, 255)); y += int(f.size * 1.2)
    return y

def bullets(d, pts, th, x, y, mw, size=44):
    acc = th[2]
    f = F(semi, size)
    for i, p in enumerate(pts, 1):
        bl = wrap(d, p, f, mw - 80)
        d.ellipse((x, y+4, x+52, y+56), fill=acc)
        nf = F(bold, 28); tw = d.textlength(str(i), font=nf)
        d.text((x+26-tw/2, y+8), str(i), font=nf, fill=th[0])
        ty = y + 2
        for b in bl: d.text((x+74, ty), b, font=f, fill=(255, 255, 255)); ty += int(size*1.28)
        y = max(y+84, ty+22)
    return y

def cards(canvas, pts, th, y, x0=60, x1=1020, maxy=H-BAND-40):
    """stacked rounded cards, auto height"""
    d = ImageDraw.Draw(canvas); acc = th[2]
    n = len(pts); gap = 22
    ch = min(190, (maxy - y - gap*(n-1)) // n)
    size = 48 if ch >= 150 else (42 if ch >= 120 else 36)
    f = F(semi, size)
    for i, p in enumerate(pts, 1):
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((x0, y, x1, y+ch), radius=28, fill=(255, 255, 255, 30), outline=acc + (200,), width=2)
        canvas.alpha_composite(ov); d = ImageDraw.Draw(canvas)
        d.ellipse((x0+24, y+ch//2-30, x0+84, y+ch//2+30), fill=acc)
        nf = F(bold, 32); tw = d.textlength(str(i), font=nf)
        d.text((x0+54-tw/2, y+ch//2-24), str(i), font=nf, fill=th[0])
        lines = wrap(d, p, f, x1-x0-150)[:2]
        ty = y + ch//2 - len(lines)*int(size*1.2)//2
        for ln in lines: d.text((x0+110, ty), ln, font=f, fill=(255, 255, 255)); ty += int(size*1.2)
        y += ch + gap
    return y

with open(data_path, encoding="utf-8") as source:
    items = json.load(source)
if not isinstance(items, list) or not items:
    raise ValueError("Instagram input must be a non-empty JSON list.")
seen_numbers = set()
for item in items:
    if not isinstance(item, dict) or not {"n", "h", "pts"}.issubset(item):
        raise ValueError("Each Instagram item must contain n, h and pts.")
    if not isinstance(item["n"], int) or item["n"] < 1 or item["n"] in seen_numbers:
        raise ValueError(f"Instagram post number must be a unique positive integer: {item.get('n')}")
    if not isinstance(item["h"], str) or not item["h"].strip():
        raise ValueError(f"Instagram post {item['n']} has an empty headline.")
    if not isinstance(item["pts"], list) or not item["pts"] or not all(isinstance(p, str) and p.strip() for p in item["pts"]):
        raise ValueError(f"Instagram post {item['n']} must have a non-empty list of text points.")
    seen_numbers.add(item["n"])

for item in items:
    n = item["n"]
    th = THEMES[(n * 5 + n // 6) % len(THEMES)]
    lay = n % 4
    if not SHOW_PHOTO and lay < 2: lay = 2 + (n // 4) % 2
    canvas = background(th, n + lay)
    d = ImageDraw.Draw(canvas)
    src = (pa if n % 2 else pb) if SHOW_PHOTO else None
    face = None
    if lay == 0:   # person bottom-right, bullets left
        pw = 700 if src is pa else 600
        canvas = paste_person(canvas, src, pw, W-pw+15, H-BAND+2)
        d = ImageDraw.Draw(canvas)
        y = headline(d, item, th, 60, 70, W-120)
        bullets(d, item["pts"], th, 60, y+30, 500)
        right = "SAVE THIS POST"
    elif lay == 1:  # person bottom-left, text right
        pw = 680 if src is pa else 560
        canvas = paste_person(canvas, src, pw, -20, H-BAND+2, flip=False)
        d = ImageDraw.Draw(canvas)
        y = headline(d, item, th, 60, 70, W-120, 80)
        bullets(d, item["pts"], th, 575, max(y+40, 480), 460, 40)
        right = "FOLLOW FOR MORE"
    elif lay == 2:  # no big person: cards
        face = badge(src, 84, th[2]) if SHOW_PHOTO else None
        y = headline(d, item, th, 60, 80, W-120, 88)
        cards(canvas, item["pts"], th, y+40)
        right = "SAVE THIS POST"
    else:           # small circular face top-right, cards
        hw = 620 if SHOW_PHOTO else W-120
        if SHOW_PHOTO:
            fb = badge(src, 150, th[2]); canvas.paste(fb, (W-60-fb.width, 70), fb)
        d = ImageDraw.Draw(canvas)
        y = headline(d, item, th, 60, 80, hw, 76 if SHOW_PHOTO else 88, 4)
        cards(canvas, item["pts"], th, max(y+40, 330))
        right = "SEND TO A FRIEND"
    d = ImageDraw.Draw(canvas)
    band(canvas, th, right, face)
    canvas.convert("RGB").save(os.path.join(out_dir, f"{n:02d}.jpg"), quality=90, optimize=True)
print("ok")


# ---------------------------------------------------------------- carousels
# If carousels.json sits next to this script, every slide is rendered as
# <out_dir>/c<NN>_<k>.jpg (1080x1350). One theme per carousel, themes rotate.
def render_carousels(path, out_dir):
    with open(path, encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, list) or not data:
        raise ValueError("Carousel input must be a non-empty JSON list.")
    seen_numbers = set()
    for item in data:
        if not isinstance(item, dict) or not {"n", "slides"}.issubset(item):
            raise ValueError("Each carousel must contain n and slides.")
        n, slides = item["n"], item["slides"]
        if not isinstance(n, int) or n < 1 or n in seen_numbers:
            raise ValueError(f"Carousel number must be a unique positive integer: {n}")
        if not isinstance(slides, list) or not slides:
            raise ValueError(f"Carousel {n} must contain at least one slide.")
        for slide in slides:
            if not isinstance(slide, dict) or not isinstance(slide.get("h"), str) or not slide["h"].strip():
                raise ValueError(f"Carousel {n} contains a slide with no headline.")
            if slide.get("kind", "text") not in {"cover", "text", "cta"}:
                raise ValueError(f"Carousel {n} contains unsupported slide kind: {slide.get('kind')}")
            if slide.get("kind", "text") != "cover" and not isinstance(slide.get("t"), str):
                raise ValueError(f"Carousel {n} slide text must be a string.")
        seen_numbers.add(n)
    for item in data:
        n, slides = item["n"], item["slides"]
        th = THEMES[(n * 5 + n // 6 + 2) % len(THEMES)]
        acc, total = th[2], len(slides)
        cv = n % 3
        src = (pa if n % 2 else pb) if SHOW_PHOTO else None
        for k, sl in enumerate(slides, 1):
            canvas = background(th, n + k)
            d = ImageDraw.Draw(canvas)
            kind = sl.get("kind", "text")
            face = badge(src, 84, acc) if (SHOW_PHOTO and kind != "cover") else None
            if kind == "cover" and not SHOW_PHOTO:
                d.rectangle((60, 300, 190, 316), fill=acc)
                f, ls = fit(d, sl["h"], bold, 120, 900, 4, 70); y = 360
                for ln in ls: d.text((60, y), ln, font=f, fill=(255, 255, 255)); y += int(f.size * 1.2)
                pill = F(bold, 44); tw = d.textlength("SWIPE  >", font=pill)
                d.rounded_rectangle((60, y + 40, 60 + tw + 50, y + 120), radius=40, fill=acc)
                d.text((85, y + 52), "SWIPE  >", font=pill, fill=th[0])
            elif kind == "cover":
                if cv == 0:
                    pw = 700 if src is pa else 600
                    canvas = paste_person(canvas, src, pw, W - pw + 15, H - BAND + 2)
                    d = ImageDraw.Draw(canvas)
                    f, ls = fit(d, sl["h"], bold, 96, 900, 4, 60)
                    y = 175; d.rectangle((60, 130, 150, 140), fill=acc)
                    for ln in ls: d.text((60, y), ln, font=f, fill=(255, 255, 255)); y += int(f.size * 1.2)
                elif cv == 1:
                    pw = 680 if src is pa else 560
                    canvas = paste_person(canvas, src, pw, -20, H - BAND + 2)
                    d = ImageDraw.Draw(canvas)
                    f, ls = fit(d, sl["h"], bold, 92, 900, 4, 60)
                    y = 175; d.rectangle((60, 130, 150, 140), fill=acc)
                    for ln in ls: d.text((60, y), ln, font=f, fill=(255, 255, 255)); y += int(f.size * 1.2)
                else:
                    fb = badge(src, 300, acc); canvas.paste(fb, ((W - fb.width) // 2, 120), fb)
                    d = ImageDraw.Draw(canvas)
                    f, ls = fit(d, sl["h"], bold, 92, 900, 4, 60)
                    y = 500
                    for ln in ls:
                        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=(255, 255, 255)); y += int(f.size * 1.2)
                pill = F(bold, 40); tw = d.textlength("SWIPE  >", font=pill)
                px = 60 if cv < 2 else (W - tw - 80) / 2
                py = (y + 30) if cv < 2 else y + 40
                d.rounded_rectangle((px, py, px + tw + 40, py + 70), radius=35, fill=acc)
                d.text((px + 20, py + 8), "SWIPE  >", font=pill, fill=th[0])
            elif kind == "cta":
                d.rectangle((60, 260, 150, 270), fill=acc)
                f, ls = fit(d, sl["h"], bold, 92, 900, 3, 60); y = 305
                for ln in ls: d.text((60, y), ln, font=f, fill=(255, 255, 255)); y += int(f.size * 1.2)
                f2 = F(semi, 52); y += 30
                for ln in wrap(d, sl["t"], f2, 900): d.text((60, y), ln, font=f2, fill=(235, 241, 255)); y += 68
                bx, by = 60, y + 50
                d.rounded_rectangle((bx, by, bx + 560, by + 120), radius=60, fill=acc)
                tw = d.textlength("DM  AUTOMATE", font=F(bold, 54))
                d.text((bx + (560 - tw) / 2, by + 28), "DM  AUTOMATE", font=F(bold, 54), fill=th[0])
            else:
                tile = str(sl.get("tile", k - 1))
                big = F(bold, 620)  # faint watermark number
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
                od.text((W - 40, 330), tile, font=big, fill=(255, 255, 255, 16), anchor="ra")
                canvas.alpha_composite(ov); d = ImageDraw.Draw(canvas)
                d.ellipse((60, 230, 200, 370), fill=acc)
                tf = F(bold, 64 if len(tile) < 2 else 50); tw = d.textlength(tile, font=tf)
                d.text((130 - tw / 2, 256 if len(tile) < 2 else 266), tile, font=tf, fill=th[0])
                f, ls = fit(d, sl["h"], bold, 100, 900, 2, 56); y = 430
                for ln in ls: d.text((60, y), ln, font=f, fill=(255, 255, 255)); y += int(f.size * 1.2)
                f2 = F(semi, 62); body = wrap(d, sl["t"], f2, 840)
                while len(body) > 5 and f2.size > 38:
                    f2 = F(semi, f2.size - 4); body = wrap(d, sl["t"], f2, 840)
                lh = int(f2.size * 1.35); y += 30
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
                od.rounded_rectangle((60, y, 1020, y + len(body) * lh + 70), radius=32, fill=(255, 255, 255, 28), outline=acc + (170,), width=2)
                od.rectangle((60, y + 30, 70, y + len(body) * lh + 40), fill=acc + (255,))
                canvas.alpha_composite(ov); d = ImageDraw.Draw(canvas)
                ty = y + 35
                for ln in body: d.text((100, ty), ln, font=f2, fill=(238, 243, 255)); ty += lh
            # progress dots above the band
            dx = W // 2 - total * 18 + 9
            for i in range(total):
                r = 8 if i + 1 == k else 5
                d.ellipse((dx + i * 36 - r, H - BAND - 34 - r, dx + i * 36 + r, H - BAND - 34 + r),
                          fill=acc if i + 1 == k else (255, 255, 255))
            band(canvas, th, f"{k}/{total}", face)
            canvas.convert("RGB").save(os.path.join(out_dir, f"c{n:02d}_{k}.jpg"), quality=90, optimize=True)
    print(f"carousels ok: {len(data)} sets")

_cp = os.path.join(HERE, "carousels.json")
if os.path.exists(_cp):
    render_carousels(_cp, out_dir)