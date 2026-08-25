import logging
import warnings

# LangGraph serialises a structured-output response whose `parsed` field the
# OpenAI stub types as None. Once per `classify` turn, and only when streaming.
PYDANTIC_PARSED_FIELD_WARNING = r"(?s).*field_name='parsed'"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    )
    logging.captureWarnings(True)
    warnings.filterwarnings("ignore", message=PYDANTIC_PARSED_FIELD_WARNING, category=UserWarning)


def truncate(value: object, limit: int = 200) -> str:
    """`str(value)`, cut to `limit` chars with a `(N chars)` marker if it overflowed."""
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}...({len(text)} chars)"
