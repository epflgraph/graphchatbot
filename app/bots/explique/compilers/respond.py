from enum import StrEnum
from typing import Any, Mapping

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, ConfigDict

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueTask, ExpliqueTurnsCompiler
from app.bots.explique.models import (
    MessageEvent,
    Persistence,
    RejectedResponse,
    SessionSummary,
    StudentIntent,
    StudentState,
)
from app.bots.explique.tutor_action import TutorAction
from app.bots.transcript import last_tool_results
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.compilation.dialog import DialogTurnsContext

# Tutor actions that get the plan's `direction` field.
_DIRECTION_ACTIONS = (TutorAction.CHALLENGE_MASTERY,)

# Actions/persistence levels that get a representation switch instead of another reworded question.
_SWITCH_ACTIONS = (TutorAction.PROBE, TutorAction.HINT, TutorAction.CHALLENGE_MISCONCEPTION)
_SWITCH_PERSISTENCE = (Persistence.STUCK, Persistence.STALLED)


class ResponseContext(DialogTurnsContext):
    rejected_responses: tuple[RejectedResponse, ...]
    lang_code: str | None


class SummaryResponseContext(ResponseContext):
    session_summary: SessionSummary
    sources: str


class PlanDirective(BaseModel):
    """The plan's direction and reasoning; empty unless this move is in `_DIRECTION_ACTIONS`."""

    model_config = ConfigDict(frozen=True)

    direction: str = ""
    reasoning: str = ""


class TutoringResponseContext(ResponseContext):
    """The teaching move, and the internal pieces that shape it."""

    student_state: StudentState
    tutor_action: TutorAction
    action_template: str
    plan_directive: PlanDirective
    points_tested: tuple[str, ...]
    switch_representation: bool


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


class SocialResponseCompiler(ResponseCompiler):
    """Small talk, or a request that has nothing to do with the course."""

    config = response_config(
        overrides=(StudentIntent.CHIT_CHAT, StudentIntent.OFF_TOPIC),
        system_template="intent-social.md",
    )


class SkipResponseCompiler(ResponseCompiler):
    """The student is dropping the current topic without naming the next one."""

    config = response_config(overrides=(StudentIntent.SKIP_TOPIC,), system_template="intent-skip.md")


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


class NewTopicResponseCompiler(ResponseCompiler):
    """The student named a topic."""

    config = response_config(overrides=(StudentIntent.NEW_TOPIC,), system_template="intent-new-topic.md")


class EndSessionResponseCompiler(ResponseCompiler):
    """The closing recap. The reply that both carries and cites sources."""

    config = response_config(overrides=(StudentIntent.END_SESSION,), system_template="intent-end.md")
    context_class = SummaryResponseContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {
            "session_summary": state["session_summary"],
            "sources": last_tool_results(state["original_messages"]),
        }


class PracticeUnavailableResponseCompiler(ResponseCompiler):
    """The apology for a practice request the practice node could not fill.

    A practice request that *was* filled never reaches a compiler: the rendered
    quiz is returned verbatim, with no model call at all.
    """

    config = response_config(
        overrides=(StudentIntent.REQUEST_PRACTICE,),
        system_template="intent-practice-unavailable.md",
    )


class TutoringResponseCompiler(ResponseCompiler):
    """The Socratic move itself.

    `intent-in-topic.md` carries the rules that hold for every move.
    `intent-in-topic-turn.md` carries what this turn alone decided — the
    assessment and the selected move — and includes a separate template file
    named after that move (e.g. `action-hint.md`)."""

    config = response_config(
        overrides=(StudentIntent.IN_TOPIC_RESPONSE,),
        system_template="intent-in-topic.md",
        user_template="intent-in-topic-turn.md",
    )
    context_class = TutoringResponseContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        student_state = state["student_state"]
        tutor_action = state["tutor_action"]
        plan = state["challenge_plan"]
        has_plan = plan is not None

        # `direction` is further restricted to challenge-mastery (`_DIRECTION_ACTIONS`).
        has_direction = has_plan and tutor_action in _DIRECTION_ACTIONS
        plan_directive = (
            PlanDirective(direction=plan.direction, reasoning=plan.reasoning) if has_direction else PlanDirective()
        )
        points_tested = tuple(plan.points_tested) if has_plan else ()
        switch_representation = student_state.persistence in _SWITCH_PERSISTENCE and tutor_action in _SWITCH_ACTIONS

        return super().context_fields(bot, state) | {
            "student_state": student_state,
            "tutor_action": tutor_action,
            "action_template": f"action-{tutor_action}.md",
            "plan_directive": plan_directive,
            "points_tested": points_tested,
            "switch_representation": switch_representation,
        }


# Which compiler answers each category, from the `overrides` each one declares.
_COMPILER_BY_CATEGORY = {
    category: compiler
    for compiler in (
        SocialResponseCompiler,
        SkipResponseCompiler,
        ContentUnreadableResponseCompiler,
        NewTopicResponseCompiler,
        EndSessionResponseCompiler,
        PracticeUnavailableResponseCompiler,
        TutoringResponseCompiler,
    )
    for category in compiler.config.overrides
}


class UnassignedCategoryError(KeyError):
    """No compiler is assigned to this category."""

    def __init__(self, category: StrEnum):
        known = [str(cat) for cat in _COMPILER_BY_CATEGORY]
        super().__init__(f"No compiler for category {category!s}. Assigned categories: {known!r}")


def compiler_for(category: StrEnum) -> type[ResponseCompiler]:
    """Get the compiler for a given category."""

    compiler = _COMPILER_BY_CATEGORY.get(category)
    if compiler is None:
        raise UnassignedCategoryError(category)
    return compiler
