import logging

from langchain_core.messages import BaseMessage, ToolCall
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot, BotState
from app.bots.callbacks.base import ToolRound, ToolRoundCallbacks, ToolRoundContext, run_callbacks

logger = logging.getLogger(__name__)


# What a tool call that raised gets logged as, and what it reports to the model.
# The instruction is mechanical: left to itself the model retries a dead tool
# until the round budget runs out, and then answers nothing.
# FUTURE: the presentational half — telling the user the answer is not based on
# tool results — belongs with the prompt instructions rather than here.
TOOL_FAILURE = "The tool call failed and returned no result."
TOOL_FAILURE_INSTRUCTION = f"{TOOL_FAILURE} Do not retry it; answer with what you already have."


def tool_failed(error: Exception) -> str:
    """What the model is handed instead of a tool result that raised."""
    logger.error(TOOL_FAILURE, exc_info=error)
    return TOOL_FAILURE_INSTRUCTION


class ToolsNode:
    """Executes all tool calls in the last message, with its round callbacks around them.

    Callable as a LangGraph node: `await node(state, runtime)`.

    Where the result goes is not this node's decision: it returns control to
    `state['active_node']`, which the model node that issued the calls wrote.
    """

    def __init__(self, tools: list, tool_round_callbacks: ToolRoundCallbacks):
        self._tools_by_name = {tool.name: tool for tool in tools}
        self._tool_node = ToolNode(tools, handle_tool_errors=tool_failed)
        self._before = tool_round_callbacks.before
        self._after = tool_round_callbacks.after

    async def __call__(self, state: BotState, runtime: Runtime[Bot]) -> Command:
        tool_round_context = ToolRoundContext(state=state, runtime=runtime, tools_by_name=self._tools_by_name)
        tool_round = ToolRound(calls=list(state["messages"][-1].tool_calls))

        if answered := await run_callbacks(self._before, tool_round_context, tool_round):
            tool_round.results = answered
        elif tool_round.calls:
            logger.info("Executing %d tool call(s) in parallel", len(tool_round.calls))
            tool_round.results.extend(await self._run_tool_calls(state, tool_round.calls))

        results = await run_callbacks(self._after, tool_round_context, tool_round) or tool_round.results
        return Command(goto=state["active_node"], update={"messages": results})

    async def _run_tool_calls(self, state: BotState, tool_calls: list[ToolCall]) -> list[BaseMessage]:
        """The results of `tool_calls`, run as though they were all the last message asked for."""
        calling = state["messages"][-1].model_copy(update={"tool_calls": tool_calls})
        return (await self._tool_node.ainvoke({**state, "messages": [*state["messages"][:-1], calling]}))["messages"]


def make_tools_node(tools: list, tool_round_callbacks: ToolRoundCallbacks = ToolRoundCallbacks()) -> ToolsNode:
    """Returns a node that executes all tool calls in the last message."""
    return ToolsNode(tools, tool_round_callbacks)
