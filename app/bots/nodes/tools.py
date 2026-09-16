import json
import logging
import secrets

from langchain_core.messages import BaseMessage
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command

logger = logging.getLogger(__name__)


# What a tool call that raised gets logged as, and what it reports to the model.
# The instruction is mechanical: left to itself the model retries a dead tool
# until the round budget runs out, and then answers nothing.
# FUTURE: the presentational half — telling the user the answer is not based on
# retrieved material — belongs with the prompt instructions rather than here.
TOOL_FAILURE = "The tool call failed and returned no result."
TOOL_FAILURE_INSTRUCTION = f"{TOOL_FAILURE} Do not retry it; answer with what you already have."


def tool_failed(error: Exception) -> str:
    """What the model is handed instead of a tool result that raised."""
    logger.error(TOOL_FAILURE, exc_info=error)
    return TOOL_FAILURE_INSTRUCTION


def _unique_chunks(chunks: list, seen: set[str]) -> list:
    """`chunks` with repeats gone, keyed on the chunk's content. The overlap
    several searches return lands in here; the first occurrence of a content
    wins, which keeps each search's own ranking order intact."""
    kept = []
    for chunk in chunks:
        if isinstance(chunk, dict) and isinstance(chunk.get("content"), str):
            if chunk["content"] in seen:
                continue
            seen.add(chunk["content"])
        kept.append(chunk)
    return kept


def dedupe_tool_results(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Parallel searches overlap: keep the first occurrence of every chunk
    across all of a round's tool results, keyed on content itself — chunks
    cut from the same document share its url yet differ in content, and
    remote indexes may also return the very same chunk twice."""
    seen: set[str] = set()
    deduped = []
    for message in messages:
        if message.type != "tool":
            deduped.append(message)
            continue

        content = message.content
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                deduped.append(message)
                continue
        elif isinstance(content, list):
            parsed = content
        else:
            deduped.append(message)
            continue

        if not isinstance(parsed, list):
            deduped.append(message)
            continue

        filtered = _unique_chunks(parsed, seen)
        if len(filtered) < len(parsed):
            logger.info(f"Dropped {len(parsed) - len(filtered)} duplicate chunk(s).")
            message = message.model_copy(update={"content": json.dumps(filtered)})
        deduped.append(message)
    return deduped


def make_tools_node(tools: list):
    """
    Returns a node that executes all tool calls in the last message.

    Where the result goes is not this node's decision: it returns control to
    `state['active_node']`, which the model node that issued the calls wrote.
    """

    tool_names = {t.name for t in tools}
    _tool_node = ToolNode(tools, handle_tool_errors=tool_failed)

    async def tools_node(state, runtime: Runtime) -> Command:
        tool_calls = state["messages"][-1].tool_calls

        for i, tc in enumerate(tool_calls):
            # Fix missing tool call ids (https://github.com/langchain-ai/langgraph/issues/4717)
            if not tc["id"]:
                logger.warning("Missing tool call id, fixing with random string.")
                state["messages"][-1].tool_calls[i]["id"] = f"chatcmpl-tool-{secrets.token_hex(16)}"

            # Fix tool name being repeated (e.g. 'search_lexsearch_lex' → 'search_lex')
            if tc["name"] not in tool_names:
                for name in tool_names:
                    if name in tc["name"]:
                        logger.warning(f"Fixing repeated tool name `{tc['name']}` → `{name}`.")
                        state["messages"][-1].tool_calls[i]["name"] = name
                        break

        logger.info(f"Executing {len(tool_calls)} tool call(s) in parallel")
        result = await _tool_node.ainvoke(state)

        return Command(goto=state["active_node"], update={"messages": dedupe_tool_results(result["messages"])})

    return tools_node
