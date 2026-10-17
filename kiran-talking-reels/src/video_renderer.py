import shutil
import subprocess
from pathlib import Path


def render(img, audio, output, duration_seconds, subtitle_path=None, music_path=None):
    """Render a vertical H.264 Reel; burn in subtitles when FFmpeg supports libass."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg not found. Install FFmpeg on the hosting service.")

    cmd = [ffmpeg, "-y", "-loop", "1", "-i", str(img), "-i", str(audio)]
    if music_path:
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]

    filters = [
        "scale=1080:1920:force_original_aspect_ratio=increase",
        "crop=1080:1920",
        "zoompan=z='min(zoom+0.0005,1.08)':d=1:s=1080x1920:fps=30",
    ]
    filters.append(
        "drawtext=text='Kiran Kumar | AI Automation':fontcolor=white:fontsize=34:"
        "box=1:boxcolor=0x101828AA:boxborderw=14:x=(w-text_w)/2:y=h-180"
    )
    if subtitle_path:
        subtitle_filter = (
            "subtitles='" + str(subtitle_path).replace("\\", "/").replace(":", "\\:")
            + "':force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=250'"
        )
        filters.append(subtitle_filter)

    cmd += ["-vf", ",".join(filters), "-t", str(int(duration_seconds)), "-r", "30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"]
    if music_path:
        cmd += [
            "-filter_complex",
            "[1:a]volume=1[voice];[2:a]volume=0.08[bg];[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v", "-map", "[a]",
        ]
    cmd += ["-shortest", "-movflags", "+faststart", str(output)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode and subtitle_path:
        # Minimal FFmpeg builds may omit libass. Retry without burned-in captions;
        # the caller can still provide the downloadable SRT sidecar.
        plain_cmd = [ffmpeg, "-y", "-loop", "1", "-i", str(img), "-i", str(audio)]
        if music_path:
            plain_cmd += ["-stream_loop", "-1", "-i", str(music_path)]
        plain_cmd += ["-vf", ",".join(filters[:-1]), "-t", str(int(duration_seconds)), "-r", "30",
                      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"]
        if music_path:
            plain_cmd += [
                "-filter_complex",
                "[1:a]volume=1[voice];[2:a]volume=0.08[bg];[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
                "-map", "0:v", "-map", "[a]",
            ]
        plain_cmd += ["-shortest", "-movflags", "+faststart", str(output)]
        proc = subprocess.run(plain_cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode:
        raise RuntimeError("FFmpeg render failed: " + proc.stderr[-1800:])
    return Path(output)
