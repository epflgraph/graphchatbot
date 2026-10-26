from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, ToolCall, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict

from app.bots.base import Bot, BotState

# The `tool_choice` values that don't force a tool call.
UNFORCED_TOOL_CHOICES = (None, "auto", "none")

# FUTURE: callbacks can only read `state`. One that needs to change it should
# set ADK's `state_delta` on its actions, and the node adds that to the update it returns.


@dataclass(frozen=True)
class CallbackContext:
    """What a model callback can read about the node and the round it is on."""

    state: BotState
    runtime: Runtime[Bot]
    tools: tuple[BaseTool, ...]
    tool_round: int
    max_tool_rounds: int
    text_is_reply: bool


@dataclass
class LLMRequest:
    """The call a model node is about to make."""

    messages: list[BaseMessage]
    tools: list[BaseTool]
    tool_choice: str | None


@dataclass(frozen=True)
class ToolRoundContext:
    """What a tool round callback can read about the node and the turn."""

    state: BotState
    runtime: Runtime[Bot]
    tools_by_name: Mapping[str, BaseTool]


@dataclass
class ToolRound:
    """One round of tool calls: the calls it runs, and the results it has so far."""

    calls: list[ToolCall]
    results: list[ToolMessage] = field(default_factory=list)


BeforeModelCallback = Callable[[CallbackContext, LLMRequest], Awaitable[AIMessage | None]]
AfterModelCallback = Callable[[CallbackContext, AIMessage], Awaitable[AIMessage | None]]
BeforeToolRoundCallback = Callable[[ToolRoundContext, ToolRound], Awaitable[list[ToolMessage] | None]]
AfterToolRoundCallback = Callable[[ToolRoundContext, ToolRound], Awaitable[list[ToolMessage] | None]]


class ModelCallbacks(BaseModel):
    """The callbacks a model node runs around its model call."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    before: tuple[BeforeModelCallback, ...] = ()
    after: tuple[AfterModelCallback, ...] = ()


class ToolRoundCallbacks(BaseModel):
    """The callbacks a tools node runs around each round.

    FUTURE: per-call `before_tool`/`after_tool` callbacks go on `ToolNode`'s `awrap_tool_call`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    before: tuple[BeforeToolRoundCallback, ...] = ()
    after: tuple[AfterToolRoundCallback, ...] = ()


async def run_callbacks[C, V, R](
    callbacks: tuple[Callable[[C, V], Awaitable[R | None]], ...], callback_context: C, value: V
) -> R | None:
    """The first value a callback returns, which stops the rest; `None` once every one carried on."""
    for callback in callbacks:
        if returned := await callback(callback_context, value):
            return returned
    return None
