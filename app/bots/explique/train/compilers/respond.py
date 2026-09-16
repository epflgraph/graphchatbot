from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.respond import (
    ContentUnreadableResponseCompiler,
    PlanDirective,
    ResponseCompiler,
    ResponseContext,
    compiler_lookup,
    response_config,
    switch_representation,
)
from app.bots.explique.models import SessionSummary, StudentIntent, StudentState, TutorAction
from app.bots.transcript import last_tool_results

# Tutor actions that get the plan's `direction` field.
_DIRECTION_ACTIONS = (TutorAction.CHALLENGE_MASTERY,)


class SummaryResponseContext(ResponseContext):
    session_summary: SessionSummary
    sources: str


class TutoringResponseContext(ResponseContext):
    """The teaching move, and the internal pieces that shape it."""

    student_state: StudentState
    tutor_action: TutorAction
    action_template: str
    plan_directive: PlanDirective
    points_tested: tuple[str, ...]
    switch_representation: bool


class SocialResponseCompiler(ResponseCompiler):
    """Small talk, or a request that has nothing to do with the course."""

    config = response_config(
        overrides=(StudentIntent.CHIT_CHAT, StudentIntent.OFF_TOPIC),
        system_template="intent-social.md",
    )


class SkipResponseCompiler(ResponseCompiler):
    """The student is dropping the current topic without naming the next one."""

    config = response_config(overrides=(StudentIntent.SKIP_TOPIC,), system_template="intent-skip.md")


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

        return super().context_fields(bot, state) | {
            "student_state": student_state,
            "tutor_action": tutor_action,
            "action_template": f"action-{tutor_action}.md",
            "plan_directive": plan_directive,
            "points_tested": points_tested,
            "switch_representation": switch_representation(student_state, tutor_action),
        }


compiler_for = compiler_lookup(
    SocialResponseCompiler,
    SkipResponseCompiler,
    ContentUnreadableResponseCompiler,
    NewTopicResponseCompiler,
    EndSessionResponseCompiler,
    PracticeUnavailableResponseCompiler,
    TutoringResponseCompiler,
)
