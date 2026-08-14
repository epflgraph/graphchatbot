import asyncio
import json
import logging
import time
from typing import AsyncGenerator

from langchain_core.runnables import RunnableConfig
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from openai.types.chat.completion_create_params import CompletionCreateParams

from app.bots.base import Bot
from app.config import config

logger = logging.getLogger(__name__)

langfuse = Langfuse(
    host=config.langfuse.host,
    secret_key=config.langfuse.secret_key,
    public_key=config.langfuse.public_key,
    environment=config.langfuse.environment,
)

# Supersteps one turn may take before the graph gives up. Explique caps its own
# retrieval rounds; every other family loops with nothing else to stop a model
# that keeps calling a tool — and LangGraph's default does not fire for these graphs.
GRAPH_RECURSION_LIMIT = 25


def agent_config(bot: Bot) -> RunnableConfig:
    """The config one turn runs under, built per request for its own trace."""
    return {
        "callbacks": [CallbackHandler()],
        "metadata": {"langfuse_tags": [bot.name]},
        "recursion_limit": GRAPH_RECURSION_LIMIT,
    }


async def generate_completion(chat_request: CompletionCreateParams, bot: Bot) -> dict:
    messages = list(chat_request["messages"])
    logger.info(f"Received non-streaming request for bot `{bot.name}` with {len(messages)} message(s)")

    agent_input = {"messages": messages}
    agent_state = await bot.graph.ainvoke(input=agent_input, config=agent_config(bot), context=bot)
    content = agent_state["messages"][-1].content

    return {
        "id": "1",
        "object": "chat.completion",
        "created": time.time(),
        "model": chat_request["model"],
        "choices": [{"message": {"role": "assistant", "content": content}}],
    }


async def agenerate_completion(chat_request: CompletionCreateParams, bot: Bot) -> AsyncGenerator:
    messages = list(chat_request["messages"])
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

            sse_chunk = {
                "id": "1",
                "object": "chat.completion.chunk",
                "created": time.time(),
                "model": chat_request["model"],
                "choices": [{"delta": {"content": chunk_text}}],
            }

            yield f"data: {json.dumps(sse_chunk)}\n\n"

    except asyncio.CancelledError:
        logger.warning("Client disconnected, stream cancelled")
    except Exception as e:
        logger.error(f"Streaming failed for bot `{bot.name}`, model `{chat_request['model']}`: {type(e).__name__}: {e}")
    finally:
        yield "data: [DONE]\n\n"
