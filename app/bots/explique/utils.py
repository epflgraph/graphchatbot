def collapse_whitespace(text: str) -> str:
    """`text` with whitespace collapsed to a single space, and none at its ends."""
    return " ".join(text.split())
