def casefold_and_collapse_whitespace(text: str) -> str:
    """Casefold the input text, collapse its whitespace to single spaces and strip its ends."""
    return " ".join(text.split()).casefold()
