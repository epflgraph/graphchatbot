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
