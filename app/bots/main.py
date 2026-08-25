import asyncio
import json
import logging
import time
from typing import AsyncGenerator

from langchain_core.messages import convert_to_messages
from langchain_core.runnables import RunnableConfig
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from openai.types.chat.completion_create_params import CompletionCreateParams

from app.bots.base import Bot
from app.bots.languages import no_answer
from app.config import config
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


async def generate_completion(chat_request: CompletionCreateParams, bot: Bot) -> dict:
    messages = drop_system_messages(convert_to_messages(chat_request["messages"]))
    logger.info(f"Received non-streaming request for bot `{bot.name}` with {len(messages)} message(s)")

    agent_input = {"messages": messages}
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


async def agenerate_completion(chat_request: CompletionCreateParams, bot: Bot) -> AsyncGenerator:
    messages = drop_system_messages(convert_to_messages(chat_request["messages"]))
    logger.info(f"Received streaming request for bot `{bot.name}` with {len(messages)} message(s)")

    agent_input = {"messages": messages}
    try:
        async for chunk, metadata in bot.graph.astream(
            input=agent_input, config=agent_config(bot), context=bot, stream_mode="messages"
        ):
            if metadata.get("langgraph_node") not in bot.model_nodes:
                continue
            chunk_text = chunk.content if isinstance(chunk.content, str) else ""
            if not chunk_text:
                continue

            yield sse_chunk(chunk_text, chat_request["model"])

    except asyncio.CancelledError:
        logger.warning("Client disconnected, stream cancelled")
    except Exception:
        logger.exception("Streaming failed for bot %r, model %r", bot.name, chat_request["model"])
        # The 200 went out with the first chunk, so the only way left to tell the
        # user is in the reply itself: silence here reads as the bot ignoring them.
        yield sse_chunk(no_answer(None), chat_request["model"])
    finally:
        yield "data: [DONE]\n\n"
