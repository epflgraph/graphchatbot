import logging

from langchain_core.messages import HumanMessage, ToolCall, ToolMessage

from app.bots.callbacks.base import UNFORCED_TOOL_CHOICES, CallbackContext, LLMRequest, ToolRound, ToolRoundContext
from app.compilation.templates import render_prompt
from app.llms.utils import flatten_content

logger = logging.getLogger(__name__)

# What a `return_direct` call made alongside others gets instead of running:
# it would write the reply before their results are in.
CALL_ALONE_INSTRUCTION = "Not run: call this tool on its own, once the other tools' results are in."

# What a `return_direct` call that came back blank reports instead: left blank, it reads to the model as shown.
NO_OUTPUT_INSTRUCTION = "Nothing was shown: the tool returned no output. Answer in plain text instead."

# Closes the first pass past the round budget after the compiler's "no tool calls left", naming the exception.
TOOL_ROUNDS_EXHAUSTED_TEMPLATE = "tool-rounds-exhausted-return-direct.md"


def is_return_direct(tool_round_context: ToolRoundContext, call: ToolCall) -> bool:
    """Whether `call` calls a `return_direct` tool."""
    tool = tool_round_context.tools_by_name.get(call["name"])
    return tool is not None and tool.return_direct


def is_forced_to_return_direct(llm_request: LLMRequest) -> bool:
    """Whether `llm_request` forces a `return_direct` tool by name, which asks for its output as the reply."""
    return any(tool.return_direct and tool.name == llm_request.tool_choice for tool in llm_request.tools)


async def withhold_return_direct_tools_when_forced(callback_context: CallbackContext, llm_request: LLMRequest) -> None:
    """Keeps `return_direct` tools off a round forced to call a tool, since forcing one means "not the answer yet"."""
    if llm_request.tool_choice in UNFORCED_TOOL_CHOICES or not any(tool.return_direct for tool in llm_request.tools):
        return
    if is_forced_to_return_direct(llm_request):
        return

    other_tools = [tool for tool in llm_request.tools if not tool.return_direct]
    if other_tools:
        llm_request.tools = other_tools
    else:
        llm_request.tool_choice = None


async def keep_only_return_direct_tools_past_budget(callback_context: CallbackContext, llm_request: LLMRequest) -> None:
    """Leaves `return_direct` tools as the only ones callable on the first pass past the round budget, and says so."""
    return_direct_tools = [tool for tool in llm_request.tools if tool.return_direct]
    # Once only: offered again, a failing tool could be retried until the turn aborts.
    if callback_context.tool_round != callback_context.max_tool_rounds or not return_direct_tools:
        return

    llm_request.tools, llm_request.tool_choice = return_direct_tools, None
    search_path = callback_context.runtime.context.prompt_search_path
    tool_names = [tool.name for tool in return_direct_tools]
    llm_request.messages.append(
        HumanMessage(content=render_prompt(search_path, TOOL_ROUNDS_EXHAUSTED_TEMPLATE, tool_names=tool_names))
    )


async def hold_back_return_direct_calls(tool_round_context: ToolRoundContext, tool_round: ToolRound) -> None:
    """Answers a `return_direct` call made alongside others instead of running it."""
    if len(tool_round.calls) < 2:
        return

    return_direct_calls = [call for call in tool_round.calls if is_return_direct(tool_round_context, call)]
    if not return_direct_calls:
        return

    logger.warning("Holding back %d return_direct call(s) made alongside others.", len(return_direct_calls))
    tool_round.calls[:] = [call for call in tool_round.calls if call not in return_direct_calls]
    tool_round.results.extend(
        ToolMessage(content=CALL_ALONE_INSTRUCTION, name=call["name"], tool_call_id=call["id"])
        for call in return_direct_calls
    )


async def end_turn_on_return_direct(tool_round_context: ToolRoundContext, tool_round: ToolRound) -> None:
    """Ends the turn on a `return_direct` call that ran on its own and succeeded."""
    if len(tool_round.calls) != 1 or not is_return_direct(tool_round_context, tool_round.calls[0]):
        return

    [call] = tool_round.calls
    result = next((result for result in tool_round.results if result.tool_call_id == call["id"]), None)
    # Failed or blank, it goes back to the model to answer in plain text instead.
    if result is None or result.status == "error":
        return
    if not flatten_content(result.content).strip():
        logger.warning("Tool `%s` returned nothing; the model answers instead", call["name"])
        result.content = NO_OUTPUT_INSTRUCTION
        return

    logger.info("Tool `%s` wrote the reply", call["name"])
    tool_round_context.actions.skip_summarization = True
