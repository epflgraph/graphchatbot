import logging

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from app.bots.base import Bot, BotState
from app.compilation.base import MessageCompiler, ModelChoice
from app.llms.utils import drop_system_messages

logger = logging.getLogger(__name__)


class ModelNodeConfig(BaseModel):
    """How a model node makes its call, and where to go after it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    compiler: type[MessageCompiler] | None = None
    prompt_name: str | None = None

    # The text branch: where a plain answer goes, and whether it is this node's
    # reply or only its decision not to search. A decision is discarded; keeping
    # it would put an AI turn nobody asked for into the transcript.
    on_text: str = END
    text_is_reply: bool = True

    # The tool branch: where a search goes, and how far the loop may run. None
    # leaves it unbounded; the model may keep searching for as long as it asks to.
    on_tools: str = "tools"
    max_tool_rounds: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _prompt_has_at_most_one_source(self) -> Self:
        # `_compile_messages` prioritizes the compiler, so accepting both prompt sources
        # would quietly ignore `prompt_name` rather than mention it.
        if self.compiler is not None and self.prompt_name is not None:
            raise ValueError("compiler and prompt_name are mutually exclusive, never combined")
        return self


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
        response = await self._resolve_model(bot, tool_choice).ainvoke(self._compile_messages(bot, state))

        if not response.tool_calls:
            return self._answered(response)
        return self._searched(response, tool_rounds_made, config)

    def _resolve_model(self, bot: Bot, tool_choice: str | None) -> Runnable:
        """The model running the call, with the tools bound to it.

        The compiler picks the model when there's one, otherwise
        the bot's streaming model runs it otherwise.
        """
        compiler = self._config.compiler
        model = bot.model_for(compiler.config.model_choice if compiler is not None else ModelChoice.MAIN)
        if not self._tools:
            return model
        return model.bind_tools(self._tools, tool_choice=tool_choice, parallel_tool_calls=True)

    def _compile_messages(self, bot: Bot, state: BotState) -> list[BaseMessage]:
        """This call's messages coming from either the node's own compiler,
        or the bot's named prompt. Compiler is prioritzed."""
        if self._config.compiler is not None:
            return self._config.compiler.compile(bot, state)
        return [SystemMessage(content=bot.prompt(self._config.prompt_name))] + drop_system_messages(state["messages"])

    def _answered(self, response: AIMessage) -> Command:
        """The model responded with text instead of searching."""
        update = {"messages": [response]} if self._config.text_is_reply else None
        return Command(goto=self._config.on_text, update=update)

    def _searched(self, response: AIMessage, tool_rounds_made: int, runnable_config: RunnableConfig) -> Command:
        """The model asked for one or more tool calls, so `tools` runs them and comes back here."""
        tool_round = tool_rounds_made + 1

        # On the last round this node is allowed, `tools` carries on to `on_text`
        # instead of coming back for another search it can no longer make.
        max_tool_rounds = self._config.max_tool_rounds
        tool_rounds_exhausted = max_tool_rounds is not None and tool_round >= max_tool_rounds

        # Read rather than configured, so this can't drift from the name the
        # graph registered the node under.
        this_node = runnable_config["metadata"]["langgraph_node"]

        return Command(
            goto=self._config.on_tools,
            update={
                "messages": [response],
                "tool_round": tool_round,
                "active_node": self._config.on_text if tool_rounds_exhausted else this_node,
            },
        )


def make_model_node(tools: list, **config) -> ModelNode:
    """Returns a node that calls an LLM client with `tools` bound and routes the result.

    Keywords are `ModelNodeConfig` fields; the defaults describe the node that answers the user.
    """
    return ModelNode(tools, ModelNodeConfig(**config))
