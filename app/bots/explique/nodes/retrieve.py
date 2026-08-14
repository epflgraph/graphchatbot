from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot
from app.bots.explique.compilers import COMPILERS
from app.bots.explique.compilers.base import ExpliqueTask
from app.bots.explique.state import ExpliqueBotState


def make_retrieve_node(tools: list, on_text: str, on_tools: str, self_node: str):
    """
    Returns a node that asks the model to search, then routes on whether it did.

    Args:
        tools:     tools the model may call.
        on_text:   node to route to when no search is made.
        on_tools:  node to route to when a search is made.
        self_node: this node's own name, so a search can loop back for another
                   round (up to the cap `INTENT_TOOL_CHOICES` declares per intent).
    """

    async def retrieve_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> Command:
        bot = runtime.context
        compiler = COMPILERS.get(ExpliqueTask.RETRIEVE)
        tools_policy = bot.INTENT_TOOL_CHOICES[state["category"]]
        model = bot.model_for(compiler.config.model_choice).bind_tools(
            tools, tool_choice=tools_policy["tool_choice"], parallel_tool_calls=True
        )

        response = await model.ainvoke(compiler.compile(bot, state))

        if not response.tool_calls:
            return Command(goto=on_text)

        retrieval_round = state.get("retrieval_round", 0) + 1
        has_more_rounds = retrieval_round < tools_policy["max_rounds"]
        update = {
            "messages": [response],
            "retrieval_round": retrieval_round,
            "active_node": self_node if has_more_rounds else on_text,
        }
        return Command(goto=on_tools, update=update)

    return retrieve_node
