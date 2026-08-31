import asyncio
import logging
from typing import Callable

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable
from openai import AuthenticationError, PermissionDeniedError
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# What a call is bounded by when the client declares no usable `request_timeout`.
REQUEST_TIMEOUT = 120.0

# One element of multipart message content: a bare string, or an OpenAI-style
# `{"type": ..., ...}` part dict (text, image_url, ...).
MessagePart = str | dict

# The shape `BaseMessage.content` takes: plain text, or a list of parts — on par
# with langchain_core's own declaration (`str | list[str | dict]`).
MessageContent = str | list[MessagePart]

# One step of transcript wrangling, applied to a single turn as a conversation
# is compiled for a prompt: returns the message — unchanged, or a copy — or
# None to drop the turn from the compiled dialog entirely.
MessageCallback = Callable[[BaseMessage], BaseMessage | None]


def apply_callbacks(messages: list[BaseMessage], callbacks: tuple[MessageCallback, ...]) -> list[BaseMessage]:
    """Run every turn through `callbacks`, in order, feeding each one's output
    to the next. A turn any callback drops is skipped by the rest of them.
    """
    dialog = []
    for message in messages:
        for callback in callbacks:
            message = callback(message)
            if message is None:
                break

        if message is not None:
            dialog.append(message)

    return dialog


def flatten_part(part: MessagePart) -> str:
    """The text one content part carries, empty for a part that carries none.

    A bare string element is text: `BaseMessage.content` is `MessageContent`,
    so a list element is not guaranteed to be a dict.
    """
    if isinstance(part, str):
        return part
    return part.get("text", "") if part.get("type") == "text" else ""


def flatten_content(content: MessageContent) -> str:
    """The text of `content`, joined — multipart content keeps only its text
    parts, so images or other media types don't fill the context window."""
    if isinstance(content, str):
        return content
    return "\n".join(text for text in map(flatten_part, content) if text)


def wrap_content(content: MessageContent) -> list[dict]:
    """Content coerced into a list of parts: a bare string becomes that list's
    one text part; an already-multipart list keeps its dict elements as-is and
    wraps only the bare-string ones."""
    if not isinstance(content, list):
        return [{"type": "text", "text": content}]
    return [{"type": "text", "text": part} if isinstance(part, str) else part for part in content]


def has_image_part(content: MessageContent) -> bool:
    """Whether `content` carries at least one image part, in the same
    multipart content shape `flatten_content` reads."""
    return isinstance(content, list) and any(
        isinstance(part, dict) and part.get("type") == "image_url" for part in content
    )


# FUTURE: once message roles are standardized into a StrEnum, make this a
# `keep=(Role.HUMAN, Role.AI)` parameter instead of a hardcoded tuple.
def stringify_messages(messages: list[BaseMessage]) -> str:
    """Stringify the human/ai turns of a conversation into one text blob,
    e.g. for embedding as `dialog_history` inside a larger system prompt."""
    turns = []
    for message in messages:
        # Keep only human and ai messages
        if message.type in ("human", "ai"):
            message_content = flatten_content(message.content)
            turns.append(f"----{message.type.upper()}----\n{message_content}")

    return "\n\n".join(turns)


def flatten_message(message: BaseMessage) -> BaseMessage:
    """A copy of `message` with any multi-part content flattened to plain text —
    e.g. the OpenAI-style `[{"type": "text", "text": "..."}]` blocks an incoming
    request can carry — so the turn can be forwarded directly into a model call.
    """
    if isinstance(message.content, str):
        return message
    return message.model_copy(update={"content": flatten_content(message.content)})


def flatten_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    return [flatten_message(message) for message in messages]


def drop_system_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Return `messages` with any system turns removed.

    Some models (e.g. Qwen 3.6) reject system messages that are not the very
    first message. Stripping user-supplied system prompts before prepending the
    bot's own keeps the conversation valid and prevents users from overriding
    the bot's pedagogical instructions.
    """
    return [message for message in messages if message.type != "system"]


def wall_clock_timeout(model: Runnable) -> float:
    """The seconds a call on `model` is bounded to, from its own `request_timeout`.

    That attribute is `float | tuple | httpx.Timeout | None`, and anything but a
    plain number falls back to `REQUEST_TIMEOUT`: the point of this bound is that
    it always exists. A slow trickle of bytes resets httpx's read timeout without
    ever completing the call, so only a wall-clock cutoff bounds a stuck one.
    """
    timeout = getattr(model, "request_timeout", None)
    if isinstance(timeout, (int, float)):
        return float(timeout)

    logger.warning("Model has a non-numeric request_timeout (%r); bounding the call at %ss", timeout, REQUEST_TIMEOUT)
    return REQUEST_TIMEOUT


async def generate_response(runnable: Runnable, messages: list[BaseMessage]) -> AIMessage | None:
    """Run a call with no output schema on already-compiled messages, returning
    `None` if it fails for any reason — `generate_structured_response`'s sibling
    for the calls whose answer is prose rather than a schema.

    Takes an already-bound runnable, since what a caller binds differs per call,
    and gives back the whole message rather than its text: this is the call that
    may answer with tool calls instead of a reply.
    """
    try:
        return await asyncio.wait_for(runnable.ainvoke(input=messages), timeout=wall_clock_timeout(runnable))
    except asyncio.TimeoutError:
        logger.warning("Response timed out")
    except (AuthenticationError, PermissionDeniedError):
        logger.critical("Response call failed with invalid credentials or access")
    except Exception:
        logger.exception("Response call raised an exception")
    return None


async def generate_structured_response(
    model: BaseChatModel,
    messages: list[BaseMessage],
    output_schema: type[BaseModel],
) -> BaseModel | None:
    """Run a structured-output call on already-compiled messages, returning `None`
    if it fails for any reason: a bad parse, a provider error, invalid credentials,
    or outrunning `wall_clock_timeout`.

    Every caller has a degraded path it takes when this returns `None`, so the
    catch is broad and lives here — one policy, rather than one that treats a
    malformed reply and a transient 503 differently depending on the call site.
    Invalid credentials are logged at `CRITICAL`, since unlike the others they
    won't resolve on their own.
    """
    # Structured output is always parsed and transformed before being shown to the
    # user; the raw JSON should never appear in the token stream.
    structured_model = model.with_structured_output(output_schema).with_config({"tags": ["nostream"]})

    try:
        return await asyncio.wait_for(structured_model.ainvoke(input=messages), timeout=wall_clock_timeout(model))
    except (OutputParserException, ValidationError):
        logger.exception("Structured response failed to parse/validate")
    except asyncio.TimeoutError:
        logger.warning("Structured response timed out")
    except (AuthenticationError, PermissionDeniedError):
        logger.critical("Structured response call failed with invalid credentials or access")
    except Exception:
        logger.exception("Structured response call raised an exception")
    return None
