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
