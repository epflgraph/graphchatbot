import logging
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator
from typing_extensions import Self

from app.bots.base import Bot, BotState, StateUpdate
from app.compilation.base import MessageCompiler
from app.llms.utils import generate_structured_response

logger = logging.getLogger(__name__)


class ClassifyNodeConfig(BaseModel):
    """Settings for a classify node: the categories, the prompt, and what to do when the call fails."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # name -> {"description": str, "tool_choice": str | None}. "tool_choice" is passed to
    # bind_tools (None, "any", or a tool's name); "description" is only read by the shared
    # `ClassifyCompiler`, whose prompt lists the categories it may choose from. Names always
    # come from here, since they're what the answer is validated against.
    categories: dict[str, dict]
    # The compiler owning the classification prompt.
    compiler: type[MessageCompiler]
    # The category a failed or invalid classification becomes.
    fallback: str
    # How many times a failed reply is retried before `fallback` applies.
    max_retries: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _fallback_is_a_known_category(self) -> Self:
        if self.fallback not in self.categories:
            raise ValueError(f"fallback {self.fallback!r} is not one of the category names {list(self.categories)!r}")
        return self


class ClassifyNode:
    """Classifies a conversation into one of a bot's categories.

    Callable as a LangGraph node: `await node(state, runtime)`.
    """

    def __init__(self, config: ClassifyNodeConfig):
        self._config = config

    async def __call__(self, state: BotState, runtime: Runtime[Bot]) -> StateUpdate:
        bot = runtime.context
        compiler = self._config.compiler
        category = await self._run(bot.model_for(compiler.config.model_choice), compiler.compile(bot, state))
        return {
            "category": category,
            "tool_choice": self._config.categories[category].get("tool_choice"),
        }

    async def _run(self, model: BaseChatModel, messages: list[BaseMessage]) -> str:
        """The validated category name, falling back to `fallback` on a failed call."""
        result = await generate_structured_response(
            model, messages, self._category_schema(), max_retries=self._config.max_retries
        )

        if result is not None:
            logger.info("Classified as `%s`", result.category)
            return result.category

        logger.warning("Classify LLM call failed, defaulting to '%s'", self._config.fallback)
        return self._config.fallback

    def _category_schema(self) -> type[BaseModel]:
        """A one-off schema restricting the answer to this node's category names."""
        return create_model("Category", category=(Literal[*self._config.categories.keys()], ...))


def make_classify_node(categories: dict[str, dict], **config) -> ClassifyNode:
    """Returns a node that classifies the conversation into one of `categories`.

    Keywords are `ClassifyNodeConfig` fields.
    """
    return ClassifyNode(ClassifyNodeConfig(categories=categories, **config))
