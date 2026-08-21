from typing import TYPE_CHECKING, Any, Mapping

from langchain_core.messages import BaseMessage

from app.compilation.base import MessageCompiler, PromptContext
from app.llms.utils import stringify_messages

if TYPE_CHECKING:
    from app.bots.base import Bot


class DialogTextContext(PromptContext):
    """Context for a call whose prompt quotes the conversation."""

    dialog_history: str


class DialogTextCompiler(MessageCompiler):
    """Compiler whose prompt quotes the conversation as string,
    instead of message turns."""

    context_class = DialogTextContext

    @classmethod
    def context_fields(cls, bot: "Bot", state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"dialog_history": stringify_messages(state["messages"])}


class DialogTurnsContext(PromptContext):
    """Context for a call whose prompt includes the conversation as message turns."""

    messages: tuple[BaseMessage, ...]


class DialogTurnsCompiler(MessageCompiler):
    """Compiler whose call carries the conversation as real turns."""

    context_class = DialogTurnsContext

    @classmethod
    def context_fields(cls, bot: "Bot", state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"messages": tuple(state["messages"])}

    @classmethod
    def embedded_turns(cls, bot: "Bot", context: DialogTurnsContext) -> tuple[BaseMessage, ...]:
        return context.messages
