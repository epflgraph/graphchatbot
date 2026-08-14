from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Mapping

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict

from app.compilation.templates import render_prompt

if TYPE_CHECKING:
    from app.bots.base import Bot


class ModelChoice(StrEnum):
    """Which of a bot's clients runs a call."""

    MAIN = "main"
    LIGHT = "light"
    VISION = "vision"


class Task(StrEnum):
    """Marker base a bot family's own task enum subclasses; member-less on purpose, so this module names no specific family."""


class PromptContext(BaseModel):
    """A compiler's typed input: everything one call's templates read."""

    # Frozen down to the contents, since a list field is coerced to its declared
    # tuple. No `arbitrary_types_allowed` — it would opt future fields out of
    # both that and validation.
    model_config = ConfigDict(frozen=True, extra="forbid")


class MessageCompilerConfig(BaseModel):
    """What a compiler declares about its call; building it is what validates the compiler."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task: Task
    system_template: str
    model_choice: ModelChoice

    # The task's sub-cases this compiler overrides the default for. Empty means
    # this compiler is the only one for its task.
    overrides: tuple[StrEnum, ...] = ()

    user_template: str | None = None
    output_schema: type[BaseModel] | None = None


class MessageCompiler(ABC):
    """Compiles the messages of one LLM call."""

    # A class that shares behaviour without being a call of its own declares none.
    config: ClassVar[MessageCompilerConfig]

    @classmethod
    @abstractmethod
    def build_context(cls, bot: "Bot", state: Mapping[str, Any]) -> PromptContext:
        """The typed context for this call, from graph state."""

    @classmethod
    def compile(cls, bot: "Bot", state: Mapping[str, Any]) -> list[BaseMessage]:
        """The messages for this call, from graph state."""
        return cls.compile_messages(bot, cls.build_context(bot, state))

    @classmethod
    def compile_messages(cls, bot: "Bot", context: PromptContext) -> list[BaseMessage]:
        """The messages from an already-built context; override to shape a call differently."""
        messages = [SystemMessage(content=cls.render(bot, cls.config.system_template, context))]
        if cls.config.user_template is not None:
            messages.append(HumanMessage(content=cls.render(bot, cls.config.user_template, context)))
        return messages

    @classmethod
    def render(cls, bot: "Bot", template: str, context: PromptContext) -> str:
        """Render `template` against the bot's own context plus this call's."""
        # Spread rather than passed as one object, so a template addresses a
        # field directly (`{{ student_state }}`), not through a `context.` prefix.
        return render_prompt(bot.prompt_search_path, template, **bot.prompt_context(), **dict(context))
