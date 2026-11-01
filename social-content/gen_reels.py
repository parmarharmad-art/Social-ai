"""Create faceless, animated book-summary Reels (1080x1920).

Usage:
  python gen_reels.py book_summaries.json assets_dir out_dir [only_id]

Book mode is intentionally faceless: it uses assets/book_*.png only and never
loads person*.png. Requires Pillow, numpy, ffmpeg, and social-content/voice.py.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import wave

# Clearer, slightly slower Hindi narration unless the workflow overrides it.
os.environ.setdefault("REEL_VOICE", "hi-IN-MadhurNeural")
os.environ.setdefault("REEL_TTS_RATE", "-8%")

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice  # noqa: E402

VERSION = "v3-animated-book"
W, H, FPS, SR = 1080, 1920, 24, 44100
WHITE = (250, 250, 255)
BG = (7, 16, 38)
ACCENT = (58, 210, 255)
GOLD = (255, 198, 82)

if len(sys.argv) < 4:
    raise SystemExit("Usage: python gen_reels.py input.json assets_dir out_dir [only_id]")
DATA_PATH, ASSETS, OUT_DIR = sys.argv[1:4]
ONLY = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
os.makedirs(OUT_DIR, exist_ok=True)


def font_path():
    candidates = [
        os.path.join(ASSETS, "fonts", "NotoSansDevanagari-Bold.ttf"),
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise SystemExit("No compatible font found. Add NotoSansDevanagari-Bold.ttf to assets/fonts.")


FONT_FILE = font_path()


def fit_font(draw, text, max_width, start=68, minimum=34):
    for size in range(start, minimum - 1, -2):
        f = ImageFont.truetype(FONT_FILE, size)
        if draw.textbbox((0, 0), text, font=f)[2] <= max_width:
            return f
    return ImageFont.truetype(FONT_FILE, minimum)


def wrap_text(draw, text, font, width):
    words, lines, current = str(text).split(), [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def gradient():
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    top = np.array((7, 16, 38), dtype=float)
    bottom = np.array((20, 48, 82), dtype=float)
    for y in range(H):
        t = y / max(1, H - 1)
        arr[y, :, :] = (top * (1 - t) + bottom * t).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def load_book_cover(book_id):
    patterns = [
        os.path.join(ASSETS, "book_%02d.png" % book_id),
        os.path.join(ASSETS, "book_%d.png" % book_id),
        os.path.join(ASSETS, "book-cover-%02d.png" % book_id),
    ]
    for p in patterns:
        if os.path.isfile(p):
            return Image.open(p).convert("RGBA")
    covers = sorted(glob.glob(os.path.join(ASSETS, "book_*.png")))
    if covers:
        return Image.open(covers[(book_id - 1) % len(covers)]).convert("RGBA")
    return None


def cover_card(canvas, cover, title, author):
    d = ImageDraw.Draw(canvas)
    card = Image.new("RGBA", (690, 900), (255, 255, 255, 15))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((0, 0, 689, 899), radius=34, fill=(255, 255, 255, 18),
                         outline=(100, 190, 255, 110), width=3)
    if cover:
        cover.thumbnail((520, 650), Image.Resampling.LANCZOS)
        x, y = (690 - cover.width) // 2, 35 + (650 - cover.height) // 2
        shadow = Image.new("RGBA", cover.size, (0, 0, 0, 130))
        shadow.putalpha(cover.getchannel("A").point(lambda a: int(a * .55)))
        card.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)), (x + 8, y + 16))
        card.alpha_composite(cover, (x, y))
    else:
        cd.rounded_rectangle((85, 70, 605, 650), radius=22, fill=(17, 45, 75, 255),
                             outline=(58, 210, 255, 255), width=4)
        tf = fit_font(cd, title, 440, 52, 32)
        lines = wrap_text(cd, title, tf, 440)
        yy = 250 - 45 * len(lines)
        for line in lines:
            cd.text((345, yy), line, font=tf, fill=WHITE, anchor="mm")
            yy += 92
    title_font = fit_font(cd, title, 610, 36, 24)
    cd.text((345, 730), title, font=title_font, fill=WHITE, anchor="mm")
    author_font = fit_font(cd, author, 610, 28, 20)
    cd.text((345, 795), author, font=author_font, fill=GOLD, anchor="mm")
    canvas.alpha_composite(card, ((W - card.width) // 2, 180))


def make_frame(item, scene_index, scene_count):
    canvas = gradient()
    d = ImageDraw.Draw(canvas)
    # Soft decorative glows; no person photos are loaded or rendered.
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((650, 900, 1300, 1550), fill=(20, 130, 220, 65))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(110)))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((55, 55, 1025, 145), radius=34, fill=(255, 255, 255, 18),
                        outline=(58, 210, 255, 100), width=2)
    d.text((90, 78), "KIRAN KUMAR  •  BOOK INSIGHTS", font=ImageFont.truetype(FONT_FILE, 30),
           fill=ACCENT)

    if scene_index == 0:
        cover_card(canvas, load_book_cover(int(item.get("id", item.get("n", 1)))),
                   item.get("book", "BOOK SUMMARY"), item.get("author", ""))
        headline = item.get("hook", item.get("h", "Aaj ka book lesson"))
        hf = fit_font(d, headline, 930, 58, 36)
        lines = wrap_text(d, headline, hf, 930)
        yy = 1190
        for line in lines[:3]:
            d.text((W // 2, yy), line, font=hf, fill=WHITE, anchor="mm",
                   stroke_width=1, stroke_fill=(0, 0, 0, 90))
            yy += 78
    else:
        scenes = item.get("scenes", [])
        scene = scenes[min(scene_index - 1, len(scenes) - 1)] if scenes else {}
        overlay = scene.get("overlay", "")
        label = item.get("theme", "KEY IDEA").upper()
        d.rounded_rectangle((70, 330, 1010, 520), radius=34, fill=(255, 255, 255, 17),
                            outline=(58, 210, 255, 100), width=2)
        d.text((110, 375), label[:36], font=ImageFont.truetype(FONT_FILE, 30), fill=GOLD)
        of = fit_font(d, overlay, 850, 64, 36)
        lines = wrap_text(d, overlay, of, 850)
        yy = 680
        for line in lines[:5]:
            d.text((W // 2, yy), line, font=of, fill=WHITE, anchor="mm")
            yy += 92
        # Animated-feeling scene cards made from the original editorial copy.
        d.rounded_rectangle((110, 1260, 970, 1470), radius=32,
                            fill=(12, 38, 66, 230), outline=(58, 210, 255, 120), width=3)
        d.text((W // 2, 1365), "%02d  /  %02d" % (scene_index, scene_count),
               font=ImageFont.truetype(FONT_FILE, 54), fill=ACCENT, anchor="mm")

    # Persistent brand footer and clear CTA.
    d.rounded_rectangle((70, 1590, 1010, 1810), radius=36, fill=(3, 10, 25, 235),
                        outline=(58, 210, 255, 120), width=2)
    cta = item.get("cta", "Save karo aur follow @officialkiraankumar")
    cf = fit_font(d, cta, 850, 42, 28)
    d.text((W // 2, 1665), cta, font=cf, fill=GOLD, anchor="mm")
    d.text((W // 2, 1750), "@officialkiraankumar", font=ImageFont.truetype(FONT_FILE, 30),
           fill=WHITE, anchor="mm")
    return canvas.convert("RGB")


def audio_for(item, tmp, narration):
    clips, starts = [], []
    cursor = 0.35
    for i, text in enumerate(narration):
        path = os.path.join(tmp, "voice_%02d.mp3" % i)
        if not voice.synth(text, path):
            raise RuntimeError("Hindi voice generation failed on narration segment %d" % (i + 1))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le",
                              "-ac", "1", "-ar", str(SR), "-"], check=True,
                             capture_output=True).stdout
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        clips.append(samples)
        starts.append(cursor)
        cursor += len(samples) / SR + 0.38
    duration = max(cursor + 0.5, 8.0)
    mix = np.zeros(int(duration * SR), dtype=np.float32)
    # Very soft original instrumental bed, kept well below speech.
    t = np.arange(len(mix), dtype=np.float32) / SR
    bed = (np.sin(2 * np.pi * 110 * t) + .45 * np.sin(2 * np.pi * 164.81 * t)) * .012
    mix += bed.astype(np.float32)
    for start, samples in zip(starts, clips):
        pos = int(start * SR)
        mix[pos:pos + len(samples)] += samples * .78
    peak = max(float(np.max(np.abs(mix))), 0.01)
    mix = np.clip(mix * min(1.0, .92 / peak), -0.98, .98)
    wav_path = os.path.join(tmp, "narration.wav")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())
    # Build timed Hinglish subtitles from the exact generated speech segments.
    def stamp(seconds):
        millis = int(round(seconds * 1000))
        hours, millis = divmod(millis, 3600000)
        minutes, millis = divmod(millis, 60000)
        secs, millis = divmod(millis, 1000)
        return "%02d:%02d:%02d,%03d" % (hours, minutes, secs, millis)

    srt_path = os.path.join(tmp, "captions.srt")
    with open(srt_path, "w", encoding="utf-8") as captions:
        for index, (start, samples, spoken_text) in enumerate(zip(starts, clips, narration), 1):
            end = start + len(samples) / SR
            captions.write("%d\\n%s --> %s\\n%s\\n\\n" %
                           (index, stamp(start), stamp(end), spoken_text))
    return wav_path, duration, srt_path


def render(item):
    narration = item.get("voiceover")
    if not narration:
        narration = [item.get("h", item.get("hook", "Aaj ka important lesson"))] + item.get("pts", [])
    narration = [str(x).strip() for x in narration if str(x).strip()]
    if not narration:
        raise ValueError("No narration found for item %s" % item.get("id", item.get("n")))
    scenes = item.get("scenes", [])
    scene_count = max(1, len(scenes), len(narration))
    tmp = tempfile.mkdtemp(prefix="book_reel_")
    wav, duration, srt_path = audio_for(item, tmp, narration)

    # Scene images are timed to their matching voice segments, with a cover intro.
    frames = []
    frame_durations = []
    intro = min(2.8, max(1.8, duration * .18))
    frames.append(make_frame(item, 0, scene_count))
    frame_durations.append(intro)
    remaining = duration - intro
    per = remaining / max(1, scene_count - 1)
    for i in range(1, scene_count):
        frames.append(make_frame(item, i, scene_count))
        frame_durations.append(per)

    concat_path = os.path.join(tmp, "frames.txt")
    with open(concat_path, "w", encoding="utf-8") as f:
        for i, (frame, seconds) in enumerate(zip(frames, frame_durations)):
            p = os.path.join(tmp, "frame_%02d.png" % i)
            frame.save(p)
            f.write("file '%s'\n" % p.replace("'", "'\\''"))
            f.write("duration %.3f\n" % seconds)
        f.write("file '%s'\n" % os.path.join(tmp, "frame_%02d.png" % (len(frames)-1)))

    out = os.path.join(OUT_DIR, "%02d.mp4" % int(item.get("id", item.get("n", 1))))
    # Preserve concat-demuxer scene timestamps and generate a full 24-fps
    # video stream. zoompan(d=1) collapsed each still image to one frame,
    # causing the audio/video output to be truncated by -shortest.
    subtitle_filter = (
        "subtitles='%s':force_style='FontName=Noto Sans,FontSize=44,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,"
        "BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=420'"
    ) % srt_path.replace("\\\\", "/")
    vf = "fps=%d,%s,format=yuv420p" % (FPS, subtitle_filter)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
           "-i", concat_path, "-i", wav, "-vf", vf, "-t", "%.2f" % duration,
           "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "21", "-c:a", "aac", "-b:a", "160k",
           "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-shortest",
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True, timeout=300)
    print("Rendered", out, "|", item.get("book", "Book lesson"), "|", round(duration, 1), "sec")


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    if isinstance(records, dict):
        records = records.get("books", records.get("items", []))
    for item in records:
        item_id = int(item.get("id", item.get("n", 0)))
        if ONLY is not None and item_id != ONLY:
            continue
        render(item)
    with open(os.path.join(OUT_DIR, ".ver"), "w", encoding="utf-8") as f:
        f.write(VERSION + "\n")


if __name__ == "__main__":
    main()
