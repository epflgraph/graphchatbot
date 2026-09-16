import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langgraph.runtime import Runtime

from app.bots.base import Bot
from app.compilation.templates import render_prompt

STREAM_CHUNK_WORDS = 3
STREAM_CHUNK_DELAY_SECONDS = 0.02


@dataclass(frozen=True)
class Status:
    """A line on what the bot is doing, shown above the reply while it is on its way."""

    description: str


def announce(template: str, runtime: Runtime[Bot], **context: Any) -> None:
    """Put `template`'s line on screen before any reply. Status lines are English whatever
    the conversation's language, so no turn has to know its language first."""
    line = render_prompt(runtime.context.prompt_search_path, template, **context)
    runtime.stream_writer(Status(line.strip()))


async def stream_text(text: str, stream_writer: Callable[[str], None]) -> None:
    """Fake stream predetermined, canned text."""
    words = text.split(" ")
    for start in range(0, len(words), STREAM_CHUNK_WORDS):
        chunk = " ".join(words[start : start + STREAM_CHUNK_WORDS])
        stream_writer(chunk if start == 0 else f" {chunk}")
        await asyncio.sleep(STREAM_CHUNK_DELAY_SECONDS)
