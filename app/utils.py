def collapse_whitespace(text: str) -> str:
    """`text` with whitespace collapsed to a single space, and none at its ends."""
    return " ".join(text.split())


def strip_trailing_punctuation(text: str) -> str:
    """`text` without the full stops and commas at its end."""
    return text.rstrip(".,")


def parse_int(text: str) -> int | None:
    """The number the input text is, or None."""
    text = text.strip()
    if not text.isdecimal():
        return None

    try:
        return int(text)
    except ValueError:
        # Past the digit limit `int()` reads.
        return None


def time_label(seconds: int) -> str:
    """`seconds` as a video player shows it, e.g. 1:40:22, or 4:05 under an hour."""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"
