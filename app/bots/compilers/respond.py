from typing import TYPE_CHECKING, Any, ClassVar, Mapping

from langchain_core.messages import BaseMessage, HumanMessage

from app.bots.compilers.base import BotTask
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.compilation.dialog import DialogTurnsCompiler, DialogTurnsContext

if TYPE_CHECKING:
    from app.bots.base import Bot


class ResponseContext(DialogTurnsContext):
    """The conversation, plus whether this is the call that has to be made without available tools."""

    tool_rounds_exhausted: bool


class ResponseCompiler(DialogTurnsCompiler):
    """The reply: the bot's own system prompt, then the conversation it answers to.

    Shared by every family whose reply needs nothing but the conversation. Each
    ships its own `prompt.md`, which is what makes one class enough; a family
    that leads with more than one prompt subclasses this to name the other.
    """

    context_class = ResponseContext

    closing_template: ClassVar[str] = "tool-rounds-exhausted.md"

    config = MessageCompilerConfig(
        task=BotTask.RESPOND,
        model_choice=ModelChoice.MAIN,
        system_template="prompt.md",
    )

    @classmethod
    def context_fields(cls, bot: "Bot", state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"tool_rounds_exhausted": state.get("tool_rounds_exhausted", False)}

    @classmethod
    def closing_turns(cls, bot: "Bot", context: ResponseContext) -> tuple[BaseMessage, ...]:
        turns = super().closing_turns(bot, context)
        if not context.tool_rounds_exhausted:
            return turns
        return (*turns, HumanMessage(content=cls.render(bot, cls.closing_template, context)))
