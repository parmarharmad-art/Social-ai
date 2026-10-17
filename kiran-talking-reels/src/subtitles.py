import re


def _timestamp(seconds):
    millis = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def split_caption_lines(script, max_chars=46):
    """Split script into readable sentence/phrase captions without breaking words."""
    text = re.sub(r"\s+", " ", (script or "").strip())
    if not text:
        return []
    phrases = re.split(r"(?<=[.!?।])\s+", text)
    lines = []
    for phrase in phrases:
        words = phrase.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > max_chars and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def make_srt(script, duration_seconds=30):
    """Create approximate sentence-level SRT timings over the selected target duration."""
    lines = split_caption_lines(script)
    if not lines:
        raise ValueError("Script is empty; cannot create subtitles.")
    duration = max(1, int(duration_seconds))
    weights = [max(1, len(line.split())) for line in lines]
    total = sum(weights)
    cursor = 0.0
    entries = []
    for index, (line, weight) in enumerate(zip(lines, weights), start=1):
        start = cursor
        end = duration if index == len(lines) else cursor + duration * weight / total
        entries.append(f"{index}\n{_timestamp(start)} --> {_timestamp(end)}\n{line}")
        cursor = end
    return "\n\n".join(entries) + "\n"
