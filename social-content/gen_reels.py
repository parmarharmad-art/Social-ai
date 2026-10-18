"""Generate 1080x1920 branded Instagram reels (MP4) from a JSON file.

usage: python gen_reels.py reels.json assets_dir out_dir [only_n]
Needs: pillow, numpy, ffmpeg on PATH.
"""
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

data_path, assets, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
only = int(sys.argv[4]) if len(sys.argv) > 4 else None
os.makedirs(out_dir, exist_ok=True)

W, H, FPS = 1080, 1920, 30
BAND = 190
yellow = (255, 196, 0)
white = (255, 255, 255)


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

pose_a = Image.open(os.path.join(assets, "person_rgba.png")).convert("RGBA")
pose_a = pose_a.crop((0, 0, pose_a.width, 664))
pose_b = Image.open(os.path.join(assets, "person_b.png")).convert("RGBA")


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


PALETTES = [
    ((8, 24, 58), (16, 48, 104), (255, 196, 0), (60, 120, 230)),
    ((30, 10, 48), (92, 25, 85), (255, 112, 166), (225, 60, 180)),
    ((5, 45, 42), (12, 104, 91), (112, 255, 205), (30, 210, 170)),
    ((44, 18, 8), (130, 48, 18), (255, 180, 70), (255, 105, 40)),
    ((12, 20, 28), (45, 60, 76), (120, 220, 255), (40, 150, 220)),
    ((38, 12, 12), (115, 24, 35), (255, 220, 120), (235, 70, 85)),
    ((24, 28, 8), (78, 92, 20), (220, 255, 100), (150, 210, 40)),
    ((20, 14, 58), (60, 40, 130), (190, 160, 255), (120, 90, 255)),
]

def background(n):
    global yellow
    top_rgb, bot_rgb, accent_rgb, glow_rgb = PALETTES[(n - 1) % len(PALETTES)]
    yellow = accent_rgb
    top = np.array(top_rgb, np.float32)
    bot = np.array(bot_rgb, np.float32)
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    img = Image.fromarray(np.repeat(top * (1 - ys) + bot * ys, W, axis=1).astype(np.uint8), "RGB").convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((140, 1000, 1000, 1800), fill=glow_rgb + (120,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(120)))
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for gx in range(40, W, 60):
        for gy in range(40, H - BAND, 60):
            dd.ellipse((gx - 2, gy - 2, gx + 2, gy + 2), fill=(255, 255, 255, 22))
    return Image.alpha_composite(img, dots)


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


def paste_fade(canvas, layer, x, y, alpha, dy=0):
    if alpha <= 0:
        return
    if alpha < 1:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer = layer.copy()
        layer.putalpha(a)
    canvas.alpha_composite(layer, (int(x), int(y + dy)))


def build(item):
    n = item["n"]
    global yellow
    layout = (n - 1) % 6
    yellow = PALETTES[(n - 1) % len(PALETTES)][2]
    bg = background(n)
    d = ImageDraw.Draw(bg)

    # Alternate the two available portrait photographs and vary scale/crop/placement.
    src = pose_a if n % 2 == 1 else pose_b
    base_pw = (900 if len(item["pts"]) <= 4 else 760) if n % 2 == 1 else 660
    pw = int(base_pw * [1.0, 0.78, 0.84, 0.68, 0.92, 0.74][layout])
    ph = int(src.height * pw / src.width)
    person = src.resize((pw, ph), Image.LANCZOS)
    if layout in (1, 4):
        px = W - pw + int(pw * 0.08)
    elif layout in (2, 5):
        px = -int(pw * 0.08)
    else:
        px = (W - pw) // 2
    py = H - BAND - ph + 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", person.size, (0, 0, 0, 0))
    sh.putalpha(person.getchannel("A").point(lambda v: int(v * 0.5)))
    shadow.paste(sh, (px + 8, py + 12), sh)
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(18)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(person, (px, py), person)
    bg = Image.alpha_composite(bg, layer)

    # Distinct decorative frame for each template family.
    accents = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ad = ImageDraw.Draw(accents)
    if layout == 1:
        ad.rounded_rectangle((28, 70, W - 28, H - BAND - 30), radius=48, outline=yellow + (230,), width=5)
        ad.rectangle((0, 0, 22, H - BAND), fill=yellow + (255,))
    elif layout == 2:
        ad.rounded_rectangle((35, 65, W - 35, H - BAND - 30), radius=20, fill=(0, 0, 0, 55), outline=yellow + (255,), width=4)
        ad.rectangle((W - 24, 0, W, H - BAND), fill=yellow + (255,))
    elif layout == 3:
        ad.rounded_rectangle((35, 80, W - 35, H - BAND - 20), radius=65, outline=yellow + (220,), width=8)
        ad.ellipse((W - 190, 55, W - 65, 180), fill=yellow + (210,))
    elif layout == 4:
        ad.polygon([(0, 0), (W, 0), (W, 90), (0, 250)], fill=yellow + (255,))
        ad.rectangle((0, H - BAND - 12, W, H - BAND), fill=yellow + (255,))
    elif layout == 5:
        ad.rounded_rectangle((38, 75, W - 38, H - BAND - 25), radius=28, outline=yellow + (255,), width=6)
        ad.line((55, 300, W - 55, 300), fill=yellow + (230,), width=5)
    bg = Image.alpha_composite(bg, accents)
    d = ImageDraw.Draw(bg)

    # bottom brand band
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    fade = np.zeros((50, W, 4), np.uint8)
    fade[..., 0:3] = (6, 18, 44)
    fade[..., 3] = np.linspace(0, 255, 50, dtype=np.uint8)[:, None]
    band.paste(Image.fromarray(fade, "RGBA"), (0, H - BAND - 50))
    bd.rectangle((0, H - BAND, W, H), fill=(6, 18, 44, 245))
    if layout in (1, 3, 5):
        bd.rounded_rectangle((24, H - BAND + 10, W - 24, H - 10), radius=28, fill=(6, 18, 44, 255), outline=yellow + (255,), width=4)
    else:
        bd.rectangle((0, H - BAND, W, H - BAND + 6), fill=yellow + (255,))
    bg = Image.alpha_composite(bg, band)
    d = ImageDraw.Draw(bg)
    d.text((60, H - BAND + 36), "KIRAN KUMAR", font=ImageFont.truetype(BOLD, 62), fill=white)
    d.text((60, H - BAND + 112), "AI AUTOMATION EXPERT", font=ImageFont.truetype(SEMI, 32), fill=yellow)

    # static text layers
    heading_sizes = [104, 88, 96, 82, 100, 90]
    f_h = ImageFont.truetype(BOLD, heading_sizes[layout])
    head_lines = wrap(d, item["h"], f_h, W - (150 if layout in (1, 4) else 120))
    head = text_layer(head_lines, f_h, white, heading_sizes[layout] + 18)
    f_b = ImageFont.truetype(SEMI, 58)
    bullets = []
    for i, p in enumerate(item["pts"], 1):
        lines = wrap(d, p, f_b, W - 260)
        t = text_layer(lines, f_b, white, 70)
        row = Image.new("RGBA", (W - 120, t.height + 8), (0, 0, 0, 0))
        rd = ImageDraw.Draw(row)
        if (n - 1) % 6 in (1, 4):
            rd.rounded_rectangle((0, 4, 68, 72), radius=16, fill=yellow)
        elif (n - 1) % 6 in (2, 5):
            rd.rectangle((5, 9, 63, 67), fill=yellow)
        else:
            rd.ellipse((0, 4, 68, 72), fill=yellow)
        nf = ImageFont.truetype(BOLD, 38)
        tw = rd.textlength(str(i), font=nf)
        rd.text((34 - tw / 2, 12), str(i), font=nf, fill=(8, 24, 58))
        row.alpha_composite(t, (100, 2))
        bullets.append(row)
    f_c = ImageFont.truetype(BOLD, 50)
    cta_text = item.get("cta", "Follow @officialkiraankumar")
    cta_w = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(cta_text, font=f_c)) + 90
    cta = Image.new("RGBA", (cta_w, 100), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cta)
    cd.rounded_rectangle((0, 0, cta_w - 1, 99), 50, fill=yellow + (255,))
    cd.text((45, 18), cta_text, font=f_c, fill=(8, 24, 58))
    return bg, head, bullets, cta


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
    """Synthesize narration. Returns (starts, cta_start, dur, wav_path) or None."""
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
    layout = (item["n"] - 1) % 6
    bg, head, bullets, cta = build(item)
    tmp = tempfile.mkdtemp()
    plan = plan_audio(item, tmp)
    if plan:
        starts, dur, wav = plan
        bullet_t = [s - 0.1 for s in starts[1:1 + len(bullets)]]
        cta_start = starts[-1] - 0.1
        audio_in = ["-i", wav]
    else:
        dur = item.get("dur", 6 + 2.4 * len(item["pts"]))
        bullet_t = [1.2 + i * 2.2 for i in range(len(bullets))]
        cta_start = dur - 2.6
        audio_in = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    total = int(dur * FPS)
    out = os.path.join(out_dir, "%02d.mp4" % item["n"])
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-"] + audio_in + [
           "-t", "%.2f" % dur, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
           "-crf", "22", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    hy = [120, 165, 110, 205, 140, 170][layout]
    by0 = hy + head.height + [60, 45, 55, 35, 45, 50][layout]
    for f in range(total):
        t = f / FPS
        frame = bg.copy()
        a = ease(t / 0.7)
        paste_fade(frame, head, 60, hy, a, dy=(1 - a) * 60)
        y = by0
        for i, b in enumerate(bullets):
            a = ease((t - bullet_t[i]) / 0.6)
            paste_fade(frame, b, 60, y, a, dy=(1 - a) * 50)
            y += b.height + 36
        if t >= cta_start:
            a = ease((t - cta_start) / 0.5)
            paste_fade(frame, cta, (W - cta.width) // 2, H - BAND - 150, a, dy=(1 - a) * 40)
        d = ImageDraw.Draw(frame)
        d.rectangle((0, 0, int(W * t / dur), 10), fill=yellow + (255,))
        p.stdin.write(np.asarray(frame.convert("RGB")).tobytes())
    p.stdin.close()
    p.wait()
    print("wrote", out, "voice" if plan else "silent", "%.1fs" % dur)


for item in json.load(open(data_path)):
    if only and item["n"] != only:
        continue
    if os.path.exists(os.path.join(out_dir, "%02d.mp4" % item["n"])) and os.environ.get("SKIP_EXISTING") == "1":
        continue
    render(item)
