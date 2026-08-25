from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Mapping

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict

from app.compilation.templates import render_prompt
from app.llms.utils import MessageCallback, apply_callbacks

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
    """A compiler's typed input: what its templates read, and what its turns are built from."""

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


class MessageCompiler:
    """Compiles the messages of one LLM call."""

    # A class that shares behaviour without being a call of its own declares none.
    config: ClassVar[MessageCompilerConfig]

    # The context this call compiles from; whatever `context_fields` adds must be declared on it.
    context_class: ClassVar[type[PromptContext]] = PromptContext

    # How this compiler transforms the conversation before reading it.
    # Declared once per bot family, never per call.
    message_callbacks: ClassVar[tuple[MessageCallback, ...]] = ()

    @classmethod
    def compile(cls, bot: "Bot", state: Mapping[str, Any]) -> list[BaseMessage]:
        """The messages for this call, from graph state."""
        return cls.compile_messages(bot, cls.build_context(bot, state))

    @classmethod
    def build_context(cls, bot: "Bot", state: Mapping[str, Any]) -> PromptContext:
        """The typed context for this call, from graph state."""
        return cls.context_class(**cls.context_fields(bot, cls.apply_callbacks(state)))

    @classmethod
    def apply_callbacks(cls, state: Mapping[str, Any]) -> Mapping[str, Any]:
        """Graph state as this call reads it: `messages` transformed, `original_messages` untouched."""
        # A field like `sources` needs exactly what the callbacks may strip, so the
        # original conversation stays reachable beside the transformed one.
        messages = state["messages"]
        return {**state, "messages": apply_callbacks(messages, cls.message_callbacks), "original_messages": messages}

    @classmethod
    def context_fields(cls, bot: "Bot", state: Mapping[str, Any]) -> dict[str, Any]:
        """This compiler's own context fields. An override adds to its parent's rather
        than restating them, so a compiler declares only what it introduces."""
        return {}

    @classmethod
    def compile_messages(cls, bot: "Bot", context: PromptContext) -> list[BaseMessage]:
        """System instructions, intermediate and closing turns."""
        return [
            SystemMessage(content=cls.render(bot, cls.config.system_template, context)),
            *cls.embedded_turns(bot, context),
            *cls.closing_turns(bot, context),
        ]

    @classmethod
    def embedded_turns(cls, bot: "Bot", context: PromptContext) -> tuple[BaseMessage, ...]:
        """The turns this call embeds between its system prompt and the closing turns."""
        return ()

    @classmethod
    def closing_turns(cls, bot: "Bot", context: PromptContext) -> tuple[BaseMessage, ...]:
        """The turns that close the call."""
        if cls.config.user_template is None:
            return ()
        return (HumanMessage(content=cls.render(bot, cls.config.user_template, context)),)

    @classmethod
    def render(cls, bot: "Bot", template: str, context: PromptContext) -> str:
        """Render `template` against the bot's own context plus this call's."""
        # Spread rather than passed as one object, so a template addresses a
        # field directly (`{{ student_state }}`), not through a `context.` prefix.
        return render_prompt(bot.prompt_search_path, template, **bot.prompt_context(), **dict(context))
