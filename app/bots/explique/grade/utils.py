def parse_int(text: str) -> int | None:
    """The number the input text is, or None."""
    text = text.strip()
    return int(text) if text.isdecimal() else None
