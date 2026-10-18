import shutil
import subprocess
from pathlib import Path


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=900)


def render(img, audio, output, duration_seconds, subtitle_path=None, music_path=None, talking_video_path=None):
    """Render a vertical Reel; optionally use a genuine lip-synced source video."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg not found. Install FFmpeg on the hosting service.")

    duration = max(1, int(duration_seconds))
    if talking_video_path:
        base = [ffmpeg, "-y", "-i", str(talking_video_path), "-i", str(audio)]
    else:
        base = [ffmpeg, "-y", "-loop", "1", "-framerate", "30", "-i", str(img), "-i", str(audio)]
    if music_path:
        base += ["-stream_loop", "-1", "-i", str(music_path)]

    video_filters = [
        "scale=720:1280:force_original_aspect_ratio=increase",
        "crop=720:1280",
    ]
    if not talking_video_path:
        video_filters.append("zoompan=z='min(zoom+0.0005,1.08)':d=1:s=720x1280:fps=30")
    video_filters.append(
        "drawtext=text='Kiran Kumar | AI Automation':fontcolor=white:fontsize=26:"
        "box=1:boxcolor=0x101828AA:boxborderw=14:x=(w-text_w)/2:y=h-120"
    )

    if subtitle_path:
        safe_path = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
        video_filters.append(
            "subtitles='" + safe_path + "':force_style='FontName=DejaVu Sans,FontSize=14,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,"
            "Outline=1,Shadow=0,Alignment=2,MarginV=165'"
        )

    def build(filters, with_subtitles):
        cmd = list(base)
        vf = ",".join(filters)
        if music_path:
            # Put video and audio processing in one complex graph; mixing -vf and
            # -filter_complex on the same output can silently bypass video effects.
            graph = "[0:v]" + vf + "[v];[1:a]volume=1,apad[a1];[2:a]volume=0.08[bg];" \
                    "[a1][bg]amix=inputs=2:duration=first:dropout_transition=2,apad[a]"
            cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "[a]"]
        else:
            if talking_video_path:
                cmd += ["-map", "0:v:0", "-map", "1:a:0", "-vf", vf, "-af", "apad"]
            else:
                cmd += ["-vf", vf, "-af", "apad"]
        cmd += [
            "-t", str(duration), "-r", "30", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-threads", "1", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(output),
        ]
        return cmd

    proc = _run(build(video_filters, bool(subtitle_path)))
    if proc.returncode and subtitle_path:
        # If libass/subtitle rendering is unavailable, still deliver the video
        # and keep the SRT as a separate download in the app.
        proc = _run(build(video_filters[:-1], False))
    if proc.returncode:
        detail = (proc.stderr or proc.stdout or "Unknown FFmpeg error")[-2200:]
        raise RuntimeError("Video render failed. Try a shorter clip or upload your own voiceover. FFmpeg: " + detail)

    if not Path(output).exists() or Path(output).stat().st_size < 1000:
        raise RuntimeError("FFmpeg finished but the output MP4 is missing or too small.")
    return Path(output)
