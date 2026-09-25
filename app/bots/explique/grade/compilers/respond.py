from typing import Any, Mapping

from langchain_core.messages import BaseMessage

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
from app.bots.explique.grade.compilers.base import GradeContext, GradedTurnsCompiler
from app.bots.explique.grade.models import GradeChallengePlan, GradeStudentIntent
from app.bots.explique.grade.transcript import graded_turns
from app.bots.explique.models import StudentIntent, StudentState, TutorAction
from app.llms.utils import flatten_content


def follows_plan(plan: GradeChallengePlan | None, tutor_action: TutorAction) -> bool:
    """Whether the move gets the plan's point and direction; a probe or a misconception challenge is about what the
    student said instead."""
    return plan is not None and tutor_action not in (TutorAction.PROBE, TutorAction.CHALLENGE_MISCONCEPTION)


class GradeResponseContext(ResponseContext, GradeContext):
    """The responder's context, plus what every grade call carries."""


class GradeTutoringResponseContext(GradeResponseContext):
    """The teaching move, and the internal pieces that shape it."""

    student_state: StudentState
    tutor_action: TutorAction
    action_template: str
    plan_directive: PlanDirective
    points_applied: tuple[str, ...]
    current_point: str
    topic_exhausted: bool
    switch_representation: bool


class GradeTutoringResponseCompiler(GradedTurnsCompiler, ResponseCompiler):
    """The Socratic move itself, aimed at the one point this turn is for."""

    config = response_config(
        overrides=(StudentIntent.IN_TOPIC_RESPONSE,),
        system_template="intent-in-topic.md",
        user_template="intent-in-topic-turn.md",
    )
    context_class = GradeTutoringResponseContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        student_state = state["student_state"]
        tutor_action = state["tutor_action"]
        plan = state["challenge_plan"]
        has_plan = plan is not None
        on_plan = follows_plan(plan, tutor_action)

        plan_directive = (
            PlanDirective(direction=plan.direction, reasoning=plan.reasoning) if on_plan else PlanDirective()
        )

        return super().context_fields(bot, state) | {
            "student_state": student_state,
            "tutor_action": tutor_action,
            "action_template": f"action-{tutor_action}.md",
            "plan_directive": plan_directive,
            "points_applied": tuple(plan.points_applied) if has_plan else (),
            "current_point": state.get("current_point", "") if on_plan else "",
            "topic_exhausted": has_plan and plan.topic_exhausted,
            "switch_representation": switch_representation(student_state, tutor_action),
        }


class GradeContentUnreadableResponseCompiler(GradedTurnsCompiler, ContentUnreadableResponseCompiler):
    """The tutor's reply to an unreadable turn, told which topic the session is on."""

    context_class = GradeResponseContext


class GradeClarificationResponseContext(GradeResponseContext):
    """The tutor's last message and the student's request about it, quoted apart."""

    last_tutor_message: str
    last_student_message: str


class GradeClarificationResponseCompiler(GradedTurnsCompiler, ResponseCompiler):
    """The tutor's last question asked again differently, for a student who asked about the question itself."""

    config = response_config(
        overrides=(GradeStudentIntent.CLARIFICATION,),
        system_template="intent-clarification.md",
        user_template="intent-clarification-turn.md",
    )
    context_class = GradeClarificationResponseContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        *_, last_tutor, last_student = graded_turns(
            bot.prompt_search_path, state["topic_lock"].topic, state["messages"]
        )
        return super().context_fields(bot, state) | {
            "last_tutor_message": flatten_content(last_tutor.content),
            "last_student_message": flatten_content(last_student.content),
        }

    @classmethod
    def embedded_turns(cls, bot: Bot, context: GradeClarificationResponseContext) -> tuple[BaseMessage, ...]:
        """No conversation turns: the two last messages come quoted in the closing turn, and a rewrite needs nothing
        earlier."""
        return ()


# Only these categories reach a responder here; everything else is redirected without a model call.
compiler_for = compiler_lookup(
    GradeTutoringResponseCompiler, GradeContentUnreadableResponseCompiler, GradeClarificationResponseCompiler
)
