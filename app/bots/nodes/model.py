from langchain_core.messages import SystemMessage
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot


def make_model_node(tools: list):
    """
    Returns a model node that calls the bot's LLM with the given tools.

    Args:
        tools: list of tool functions to bind to the model. Pass [] for a no-tools node.
    """

    async def model_node(state, runtime: Runtime[Bot]) -> Command:
        bot = runtime.context

        model = bot.model.bind_tools(tools) if tools else bot.model
        messages = [SystemMessage(content=bot.system_prompt)] + state['messages']

        print('[MODEL]', f"Calling LLM with {len(tools)} tool(s)")
        ai_message = await model.ainvoke(messages)

        if ai_message.tool_calls:
            return Command(goto='tools', update={'messages': [ai_message]})
        else:
            return Command(goto=END, update={'messages': [ai_message]})

    return model_node
