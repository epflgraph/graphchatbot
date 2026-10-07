import logging
import warnings

import sentry_sdk
from sentry_sdk.integrations.langchain import LangchainIntegration
from sentry_sdk.integrations.langgraph import LanggraphIntegration
from sentry_sdk.integrations.openai import OpenAIIntegration
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

from app.config import SentryConfig

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


def strip_event_values(event: dict, hint: dict) -> dict:
    """Send Sentry an error's shape — log template, exception types, stack — but none of its values."""
    if (logentry := event.get("logentry")) is not None:
        event["logentry"] = {"message": logentry["message"]}
    for exception in event.get("exception", {}).get("values", []):
        exception.pop("value", None)
    event.pop("extra", None)
    return event


def setup_incident_report(config: SentryConfig):
    """Report every ERROR-level log and unhandled exception to Sentry; a no-op without a DSN."""
    sentry_sdk.init(
        dsn=config.dsn,
        environment=config.environment,
        # Student conversations stay out of Sentry; Langfuse owns the tracing.
        max_request_body_size="never",
        include_local_variables=False,
        # Open WebUI forwards the student's name and email as request headers, which
        # Sentry attaches to error events and does not scrub by default.
        event_scrubber=EventScrubber(denylist=[*DEFAULT_DENYLIST, "x-openwebui-user-name", "x-openwebui-user-email"]),
        max_breadcrumbs=0,
        before_send=strip_event_values,
        disabled_integrations=[LangchainIntegration(), LanggraphIntegration(), OpenAIIntegration()],
    )


def truncate(value: object, limit: int = 200) -> str:
    """`str(value)`, cut to `limit` chars with a `(N chars)` marker if it overflowed."""
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}...({len(text)} chars)"
