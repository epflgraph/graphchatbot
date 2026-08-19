import logging

from langchain_core.messages import SystemMessage
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot, BotState
from app.llms.utils import drop_system_messages

logger = logging.getLogger(__name__)


def make_model_node(
    tools: list,
    prompt_name: str | None = None,
    on_text: str = END,
    on_tools: str = "tools",
    state_update: dict | None = None,
):
    """
    Returns a model node that calls the bot's LLM and routes the result.

    Args:
        tools:        list of tool functions to bind to the model. Pass [] for a no-tools node.
        prompt_name:  name of the prompt file to resolve via bot.prompt(). Falls back to the
                      bot's own `DEFAULT_PROMPT_NAME` when omitted.
        on_text:      node to route to when the model returns a plain-text response.
                      Defaults to END for backward compatibility.
        on_tools:     node to route to when the model makes tool calls.
                      Defaults to 'tools' for backward compatibility.
        state_update: extra state fields merged into the update after the LLM call.
    """

    async def model_node(state: BotState, runtime: Runtime[Bot]) -> Command:
        bot = runtime.context

        tool_choice = state.get("tool_choice")
        if tool_choice:
            model = bot.model.bind_tools(tools, tool_choice=tool_choice)
        elif tools:
            model = bot.model.bind_tools(tools)
        else:
            model = bot.model

        messages = [SystemMessage(content=bot.prompt(prompt_name))] + drop_system_messages(state["messages"])

        logger.info(f"Calling LLM with {len(tools)} tool(s), tool_choice={tool_choice}")
        ai_message = await model.ainvoke(messages)

        update = {"messages": [ai_message], **(state_update or {})}
        return Command(goto=on_tools if ai_message.tool_calls else on_text, update=update)

    return model_node
