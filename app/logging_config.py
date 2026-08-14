import logging


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    )


def truncate(value: object, limit: int = 200) -> str:
    """`str(value)`, cut to `limit` chars with a `(N chars)` marker if it overflowed."""
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}...({len(text)} chars)"
