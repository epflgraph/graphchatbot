import asyncio
import json
import logging
import time
from typing import AsyncGenerator, AsyncIterator

from langchain_core.messages import convert_to_messages
from langchain_core.runnables import RunnableConfig
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from openai.types.chat.completion_create_params import CompletionCreateParams

from app.bots.base import Bot
from app.bots.languages import no_answer
from app.bots.utils import Status
from app.config import config
from app.identity import Requester
from app.llms.utils import drop_system_messages

logger = logging.getLogger(__name__)

langfuse = Langfuse(
    host=config.langfuse.host,
    secret_key=config.langfuse.secret_key,
    public_key=config.langfuse.public_key,
    environment=config.langfuse.environment,
)

# Supersteps one turn may take before the graph gives up. Each model node bounds
# its own tool loop, so this is the backstop for a cycle no round budget governs —
# LangGraph's own default does not fire for these graphs.
GRAPH_RECURSION_LIMIT = 25


def agent_config(bot: Bot) -> RunnableConfig:
    """The config one turn runs under, built per request for its own trace."""
    return {
        "callbacks": [CallbackHandler()],
        "metadata": {"langfuse_tags": [bot.name]},
        "recursion_limit": GRAPH_RECURSION_LIMIT,
    }


async def generate_completion(chat_request: CompletionCreateParams, bot: Bot, *, requester: Requester | None) -> dict:
    messages = drop_system_messages(convert_to_messages(chat_request["messages"]))
    logger.info(f"Received non-streaming request for bot `{bot.name}` with {len(messages)} message(s)")

    agent_input = {"messages": messages, "requester": requester}
    try:
        agent_state = await bot.graph.ainvoke(input=agent_input, config=agent_config(bot), context=bot)
    except Exception:
        # Nothing has been sent yet, so the failure can still be told honestly as
        # a 500 — unlike the streaming path, which has already committed to a 200.
        logger.exception("Completion failed for bot %r, model %r", bot.name, chat_request["model"])
        raise
    content = agent_state["messages"][-1].content

    return {
        "id": "1",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": chat_request["model"],
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    }


def sse_chunk(content: str, model_name: str) -> str:
    """One `data:` chunk of a streamed reply, carrying `content`."""
    chunk = {
        "id": "1",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_name,
        "choices": [{"index": 0, "delta": {"content": content}}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def sse_status(status: Status, *, done: bool) -> str:
    """One `data:` chunk carrying a status line for Open WebUI to show above the reply,
    which forwards the `event` object as it is; done, the line is taken down."""
    event = {"type": "status", "data": {"description": status.description, "done": done, "hidden": done}}
    return f"data: {json.dumps({'event': event})}\n\n"


async def turn_events(bot: Bot, agent_input: dict) -> AsyncGenerator[Status | str, None]:
    """The status lines and reply text of one turn, in the order the graph streams them."""
    try:
        async for mode, payload in bot.graph.astream(
            input=agent_input, config=agent_config(bot), context=bot, stream_mode=["messages", "custom"]
        ):
            if mode == "custom":
                # Payload a node wrote to the stream itself, through `runtime.stream_writer`.
                yield payload
                continue
            message_chunk, metadata = payload
            if metadata.get("langgraph_node") in bot.model_nodes and isinstance(message_chunk.content, str):
                yield message_chunk.content
    except Exception:
        logger.exception("Streaming failed for bot %r", bot.name)
        # The 200 went out with the first chunk, so the only way left to tell the
        # user is in the reply itself: silence here reads as the bot ignoring them.
        yield no_answer(bot.prompt_search_path, None)


async def sse_lines(events: AsyncIterator[Status | str], model_name: str) -> AsyncGenerator[str, None]:
    """The turn's events as SSE chunks. A status line stays up until the first text
    that follows it, or until the turn ends without any."""
    on_screen: Status | None = None
    async for event in events:
        if isinstance(event, Status):
            on_screen = event
            yield sse_status(event, done=False)
        elif event:
            if on_screen is not None:
                yield sse_status(on_screen, done=True)
                on_screen = None
            yield sse_chunk(event, model_name)
    if on_screen is not None:
        yield sse_status(on_screen, done=True)


async def agenerate_completion(
    chat_request: CompletionCreateParams, bot: Bot, *, requester: Requester | None
) -> AsyncGenerator:
    messages = drop_system_messages(convert_to_messages(chat_request["messages"]))
    logger.info(f"Received streaming request for bot `{bot.name}` with {len(messages)} message(s)")

    agent_input = {"messages": messages, "requester": requester}
    try:
        async for line in sse_lines(turn_events(bot, agent_input), chat_request["model"]):
            yield line
    except asyncio.CancelledError:
        logger.warning("Client disconnected, stream cancelled")
    finally:
        yield "data: [DONE]\n\n"
