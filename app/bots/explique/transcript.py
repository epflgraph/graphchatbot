from typing import Iterator

from langchain_core.messages import BaseMessage

from app.llms.utils import flatten_content, stringify_messages


def keep_dialog_roles(message: BaseMessage) -> BaseMessage | None:
    """Keep human and ai turns; drop everything else.

    That includes ToolMessages, and one ai turn too: the message where the
    model decides to call a tool (`tool_calls` set) carries no real content,
    just the decision to retrieve. What gets retrieved still reaches the
    prompt — just as the `<sources>` block `GroundedDialogCompiler.sources()`
    builds, never as a raw message in this history.
    """
    if message.type not in ("human", "ai") or getattr(message, "tool_calls", None):
        return None
    return message


def all_assistant_turns(messages: list[BaseMessage]) -> tuple[str, ...]:
    """Every assistant turn, as plain text."""
    return tuple(flatten_content(message.content) for message in messages if message.type == "ai")


def last_student_turn(messages: list[BaseMessage]) -> str:
    """The student's latest turn, as plain text. Read after transcription,
    so a photo turn reads as what the image said."""
    for message in reversed(messages):
        if message.type == "human":
            return flatten_content(message.content)
    return ""


def prior_turns(messages: list[BaseMessage], count: int) -> str:
    """The `count` turns before the latest one, stringified; empty at the start of
    a session."""
    return stringify_messages(messages[-(count + 1) : -1])


def _last_assistant_turns(messages: list[BaseMessage]) -> Iterator[BaseMessage]:
    """Everything the assistant did since the student's last message, oldest first"""
    tail = []
    for message in reversed(messages):
        if message.type == "human":
            break
        tail.append(message)
    return reversed(tail)


def last_tool_results(messages: list[BaseMessage]) -> str:
    """The consecutive tool results since the student's last message, as one string."""
    chunks = [str(message.content) for message in _last_assistant_turns(messages) if message.type == "tool"]
    return "\n\n".join(chunks) if chunks else "(no retrieved material)"
