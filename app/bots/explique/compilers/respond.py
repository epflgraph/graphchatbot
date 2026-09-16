from collections.abc import Callable, Iterable
from enum import StrEnum
from functools import partial
from typing import Any, Mapping

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, ConfigDict

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueTask, ExpliqueTurnsCompiler
from app.bots.explique.models import MessageEvent, Persistence, RejectedResponse, StudentState, TutorAction
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.compilation.dialog import DialogTurnsContext

# Actions/persistence levels that get a representation switch instead of another reworded question.
_SWITCH_ACTIONS = (TutorAction.PROBE, TutorAction.HINT, TutorAction.CHALLENGE_MISCONCEPTION)
_SWITCH_PERSISTENCE = (Persistence.STUCK, Persistence.STALLED)


def switch_representation(student_state: StudentState, tutor_action: TutorAction) -> bool:
    """Whether this move changes representation instead of rewording the last question."""
    return student_state.persistence in _SWITCH_PERSISTENCE and tutor_action in _SWITCH_ACTIONS


class ResponseContext(DialogTurnsContext):
    rejected_responses: tuple[RejectedResponse, ...]
    lang_code: str | None


class PlanDirective(BaseModel):
    """The plan's direction and reasoning, or empty when this move does not follow the plan."""

    model_config = ConfigDict(frozen=True)

    direction: str = ""
    reasoning: str = ""


def response_config(**declared) -> MessageCompilerConfig:
    """Every responder shares the same task and model; only what differs gets written out."""
    return MessageCompilerConfig(task=ExpliqueTask.RESPOND, model_choice=ModelChoice.MAIN, **declared)


class ResponseCompiler(ExpliqueTurnsCompiler):
    """Base for the responders: a system prompt, then the conversation, then
    whatever applies only to this turn."""

    context_class = ResponseContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {
            "rejected_responses": cls.rejected_responses(state),
            "lang_code": state.get("lang_code"),
        }

    @classmethod
    def closing_turns(cls, bot: Bot, context: ResponseContext) -> tuple[BaseMessage, ...]:
        """The task as compiled upstream, then any retry this turn has accumulated."""
        return (*super().closing_turns(bot, context), *cls.retry_turns(bot, context))

    @staticmethod
    def rejected_responses(state: Mapping[str, Any]) -> tuple[RejectedResponse, ...]:
        """The bot replies the response evaluator turned down this turn"""
        return state.get("rejected_responses") or ()

    @classmethod
    def retry_turns(cls, bot: Bot, context: ResponseContext) -> list[BaseMessage]:
        """Each rejected turn, followed by its correction."""
        turns = []
        for rejection in context.rejected_responses:
            turns.append(AIMessage(content=rejection.response))
            turns.append(HumanMessage(content=cls.render(bot, f"retry-{rejection.tag}.md", context)))
        return turns


class ContentUnreadableResponseCompiler(ResponseCompiler):
    """The latest turn's content (e.g. a photo) couldn't be read — see
    `app/bots/nodes/transcribe_image.py`.

    `category` here is a `MessageEvent`, not a `StudentIntent`: the graph sets
    it directly, the classifier never does — hence `event-`, not `intent-`,
    in the template name."""

    config = response_config(
        overrides=(MessageEvent.CONTENT_UNREADABLE,),
        system_template="event-content-unreadable.md",
    )


class UnassignedCategoryError(KeyError):
    """No compiler is assigned to this category."""

    def __init__(self, category: StrEnum, assigned: Iterable[StrEnum]):
        super().__init__(f"No compiler for category {category!s}. Assigned: {[str(cat) for cat in assigned]!r}")


def _compiler_for(by_category: Mapping[StrEnum, type[ResponseCompiler]], category: StrEnum) -> type[ResponseCompiler]:
    compiler = by_category.get(category)
    if compiler is None:
        raise UnassignedCategoryError(category, by_category)
    return compiler


def compiler_lookup(*compilers: type[ResponseCompiler]) -> Callable[[StrEnum], type[ResponseCompiler]]:
    """A `compiler_for(category)` over `compilers`, from the `overrides` each one declares."""
    by_category = {category: compiler for compiler in compilers for category in compiler.config.overrides}
    return partial(_compiler_for, by_category)
