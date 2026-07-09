import logging

from langchain_core.messages import SystemMessage
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot

logger = logging.getLogger(__name__)


def make_model_node(tools: list, prompt_name: str | None = None, state_update: dict | None = None):
    """
    Returns a model node that calls the bot's LLM with the given tools.

    Args:
        tools:        list of tool functions to bind to the model. Pass [] for a no-tools node.
        prompt_name:  name of the prompt file to resolve via bot.prompt(). Defaults to 'prompt'.
        state_update: extra state fields merged into the update when routing to tools.
    """

    async def model_node(state, runtime: Runtime[Bot]) -> Command:
        bot = runtime.context

        tool_choice = state.get('tool_choice')
        if tool_choice:
            model = bot.model.bind_tools(tools, tool_choice=tool_choice)
        elif tools:
            model = bot.model.bind_tools(tools)
        else:
            model = bot.model

        messages = [SystemMessage(content=bot.prompt(prompt_name))] + state['messages']

        logger.info(f"Calling LLM with {len(tools)} tool(s), tool_choice={tool_choice}")
        ai_message = await model.ainvoke(messages)

        if ai_message.tool_calls:
            return Command(goto='tools', update={'messages': [ai_message], **(state_update or {})})
        else:
            return Command(goto=END, update={'messages': [ai_message]})

    return model_node
