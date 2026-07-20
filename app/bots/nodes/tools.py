import logging
import secrets

from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command

logger = logging.getLogger(__name__)


def make_tools_node(tools: list, back_to: str | None = "model"):
    """
    Returns a tools node that executes all tool calls in the last message.

    Args:
        tools:   list of tool functions available to the model.
        back_to: name of the node to route to after tool execution.
                 If None, reads the destination from state['active_node'].
    """

    tool_names = {t.name for t in tools}
    _tool_node = ToolNode(tools)

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

        update = {"messages": result["messages"], "tool_choice": None}

        destination = back_to if back_to else state.get("active_node") or "model"
        return Command(goto=destination, update=update)

    return tools_node
