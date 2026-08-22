import logging

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field

from app.bots.base import Bot, BotState
from app.bots.languages import no_answer
from app.compilation.base import MessageCompiler
from app.llms.utils import flatten_content, generate_response

logger = logging.getLogger(__name__)


class ModelNodeConfig(BaseModel):
    """How a model node makes its call, and where to go after it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    compiler: type[MessageCompiler]

    # The text branch: where a plain answer goes, and whether it is this node's
    # reply or only its decision not to search. A decision is discarded; keeping
    # it would put an AI turn nobody asked for into the transcript.
    on_text: str = END
    text_is_reply: bool = True

    # The tool branch: where a search goes, and how many rounds it may take.
    # The cap always exists — unbounded, the loop runs until LangGraph aborts
    # the turn, which reaches the user as an empty reply.
    on_tools: str = "tools"
    max_tool_rounds: int = Field(default=3, ge=1)


class ModelNode:
    """Calls the bot's LLM client with its tools bound, and routes on what came back.

    Callable as a LangGraph node: `await node(state, runtime, config)`.
    """

    def __init__(self, tools: list, config: ModelNodeConfig):
        self._tools = tools
        self._config = config

    async def __call__(self, state: BotState, runtime: Runtime[Bot], config: RunnableConfig) -> Command:
        bot = runtime.context
        tool_rounds_made = state.get("tool_round", 0)
        is_first_round = tool_rounds_made == 0

        # A forced `tool_choice` happens on the first round: once the model has
        # searched, whether to search again is up to it, not the
        # classifier. Without this, the forced choice would fire on every pass.
        tool_choice = state.get("tool_choice") if is_first_round else None

        logger.info(
            "Calling LLM client with %d tool(s), round=%d, tool_choice=%s",
            len(self._tools),
            tool_rounds_made,
            tool_choice,
        )
        messages = self._config.compiler.compile(bot, state)
        response = await generate_response(self._resolve_model(bot, tool_choice, tool_rounds_made), messages)
        call_failed = response is None

        if not call_failed and response.tool_calls:
            return self._searched(response, tool_rounds_made, config)

        # Past the tool branch, so whatever came back was meant to be text.
        answered_with_nothing = not call_failed and not flatten_content(response.content).strip()

        # A failed call and a blank reply leave the student in the same place.
        if call_failed or (answered_with_nothing and self._config.text_is_reply):
            logger.warning("Model call produced nothing; falling back to NO_ANSWER")
            response = AIMessage(content=no_answer(state.get("lang_code")))

        return self._answered(response)

    def _resolve_model(self, bot: Bot, tool_choice: str | None, tool_rounds_made: int) -> Runnable:
        """The model the compiler chose, with the tools bound to it."""
        model = bot.model_for(self._config.compiler.config.model_choice)
        if not self._tools:
            return model
        # Past the budget the tools stay bound but forbidden. Omitting them would
        # instead leave a model that has searched multiple times still emitting
        # tool-call syntax, which parses to an empty reply.
        if tool_rounds_made >= self._config.max_tool_rounds:
            tool_choice = "none"
        return model.bind_tools(self._tools, tool_choice=tool_choice, parallel_tool_calls=True)

    def _answered(self, response: AIMessage) -> Command:
        """The model responded with text instead of searching."""
        update = {"messages": [response]} if self._config.text_is_reply else None
        return Command(goto=self._config.on_text, update=update)

    def _searched(self, response: AIMessage, tool_rounds_made: int, runnable_config: RunnableConfig) -> Command:
        """The model asked for one or more tool calls, so `tools` runs them and comes back here."""
        tool_round = tool_rounds_made + 1

        # Out of rounds, a decision node is done and hands over to `on_text`.
        # A reply node comes back here instead — with its tools forbidden, so it answers.
        tool_rounds_exhausted = tool_round >= self._config.max_tool_rounds
        handover = tool_rounds_exhausted and not self._config.text_is_reply

        # Read rather than configured, so this can't drift from the name the
        # graph registered the node under.
        this_node = runnable_config["metadata"]["langgraph_node"]

        return Command(
            goto=self._config.on_tools,
            update={
                "messages": [response],
                "tool_round": tool_round,
                "active_node": self._config.on_text if handover else this_node,
            },
        )


def make_model_node(tools: list, **config) -> ModelNode:
    """Returns a node that calls an LLM client with `tools` bound and routes the result.

    Keywords are `ModelNodeConfig` fields; the defaults describe the node that answers the user.
    """
    return ModelNode(tools, ModelNodeConfig(**config))
