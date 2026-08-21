from typing import TYPE_CHECKING, Any, ClassVar, Mapping

from langchain_core.messages import BaseMessage

from app.compilation.base import MessageCompiler, PromptContext
from app.llms.utils import DialogView

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
        return super().context_fields(bot, state) | {"dialog_history": cls.dialog_history(bot, state)}

    @staticmethod
    def dialog_history(bot: "Bot", state: Mapping[str, Any]) -> str:
        """The conversation so far as text, read through the bot's own view."""
        return bot.dialog.messages_str(state["messages"])


class DialogTurnsContext(PromptContext):
    """Context for a call whose prompt includes the conversation as message turns."""

    messages: tuple[BaseMessage, ...]


class DialogTurnsCompiler(MessageCompiler):
    """Compiler whose call carries the conversation as real turns."""

    # The view this call reads the conversation through; None reads the bot's own.
    dialog_view: ClassVar[DialogView | None] = None

    context_class = DialogTurnsContext

    @classmethod
    def context_fields(cls, bot: "Bot", state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"messages": cls.history(bot, state)}

    @classmethod
    def embedded_turns(cls, bot: "Bot", context: DialogTurnsContext) -> tuple[BaseMessage, ...]:
        return context.messages

    @classmethod
    def history(cls, bot: "Bot", state: Mapping[str, Any]) -> tuple[BaseMessage, ...]:
        """The conversation as this compiler sees it."""
        view = bot.dialog if cls.dialog_view is None else cls.dialog_view
        return tuple(view.messages(state["messages"]))
