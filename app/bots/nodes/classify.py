import logging
from typing import Callable, ClassVar, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict, create_model, model_validator
from typing_extensions import Self

from app.bots.base import Bot, BotState, StateUpdate
from app.compilation.base import MessageCompiler
from app.llms.utils import generate_structured_response

logger = logging.getLogger(__name__)


class ClassifyNodeConfig(BaseModel):
    """What a classify node needs: its categories, the fallback for a failed classification, and,
    optionally, the compiler owning its prompt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    categories: dict[str, dict] | Callable
    fallback: str
    compiler: type[MessageCompiler] | None = None

    @model_validator(mode="after")
    def _fallback_is_a_known_category(self) -> Self:
        # Only checkable for static categories: a callable's output depends on
        # state we don't have yet, so that case is trusted and fails loudly at
        # call time instead (an unknown key raises naturally on lookup).
        if not callable(self.categories) and self.fallback not in self.categories:
            raise ValueError(f"fallback {self.fallback!r} is not one of the category names {list(self.categories)!r}")
        return self


class ClassifyNode:
    """Classifies a conversation into one of a bot's categories.

    Callable as a LangGraph node: `await node(state, runtime)`.
    """

    DEFAULT_SYSTEM_PROMPT: ClassVar[str] = (
        "You will be given a conversation between a Human and an AI system.\n"
        "Your task is to classify the conversation based on the last request.\n"
        "The possible categories are the following:\n"
        "{categories}"
    )

    def __init__(self, config: ClassifyNodeConfig):
        self._config = config

    async def __call__(self, state: BotState, runtime: Runtime[Bot]) -> StateUpdate:
        bot = runtime.context
        categories_dict = self._resolve_categories(state)
        messages = self._compile_messages(bot, categories_dict, state)
        model = self._resolve_model(bot)
        category = await self._run(model, messages, categories_dict, self._config.fallback)
        return {
            "category": category,
            "tool_choice": categories_dict[category].get("tool_choice"),
        }

    def _resolve_categories(self, state: BotState) -> dict:
        """Static categories, or ones this bot computes from the current state."""
        categories = self._config.categories
        return categories(state) if callable(categories) else categories

    def _compile_messages(self, bot: Bot, categories_dict: dict, state: BotState) -> list[BaseMessage]:
        """This call's messages: the bot's own compiler, or the default prompt below."""
        compiler = self._config.compiler
        if compiler is not None:
            return compiler.compile(bot, state)
        return self._default_compiler(bot, categories_dict, state)

    @staticmethod
    def _default_compiler(bot: Bot, categories_dict: dict, state: BotState) -> list[BaseMessage]:
        """Built here rather than by a compiler, from the category descriptions."""
        categories_str = ClassifyNode._stringify_categories(categories_dict)
        system_prompt = ClassifyNode.DEFAULT_SYSTEM_PROMPT.format(categories=categories_str)
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=bot.dialog.messages_str(state["messages"])),
        ]

    @staticmethod
    def _stringify_categories(categories_dict: dict) -> str:
        """The categories as a bulleted `name: description` list, for the default classify prompt."""
        return "\n".join(f"* {name}: {cat['description']}" for name, cat in categories_dict.items())

    def _resolve_model(self, bot: Bot) -> BaseChatModel:
        """The client this call runs on: the compiler's choice, or the bot's light model."""
        compiler = self._config.compiler
        if compiler is not None:
            return bot.model_for(compiler.config.model_choice)
        return bot.light_model

    @staticmethod
    async def _run(model: BaseChatModel, messages: list[BaseMessage], categories_dict: dict, fallback: str) -> str:
        """The validated category name, falling back to `fallback` on a failed call."""
        result = await generate_structured_response(model, messages, ClassifyNode._category_schema(categories_dict))

        if result is not None:
            logger.info("Classified as `%s`", result.category)
            return result.category

        logger.warning("Classify LLM call failed, defaulting to '%s'", fallback)
        return fallback

    @staticmethod
    def _category_schema(categories_dict: dict) -> type[BaseModel]:
        """A one-off schema restricting the answer to this call's category names."""
        return create_model("Category", category=(Literal[*categories_dict.keys()], ...))


def make_classify_node(
    categories: dict[str, dict] | Callable, fallback: str, compiler: type[MessageCompiler] | None = None
) -> ClassifyNode:
    """Returns a node that classifies the conversation into one of `categories`.

    Args:
        categories: name -> {"description": str, "tool_choice": str | None}, or a callable of
            state returning that dict, for categories that depend on runtime state (e.g. message
            count). "tool_choice" is passed to bind_tools (None, "any", or a tool's name);
            "description" is only required without a `compiler`. Names always come from here,
            since they're what the answer is validated against.
        fallback: the category a failed or invalid classification becomes. Must name a low-risk,
            "safe to guess" category — validated against `categories` at construction when
            `categories` is a plain dict.
        compiler: the bot's own compiler for the classification prompt, if it has one; otherwise
            the prompt is built here from the descriptions above.
    """
    return ClassifyNode(ClassifyNodeConfig(categories=categories, fallback=fallback, compiler=compiler))
