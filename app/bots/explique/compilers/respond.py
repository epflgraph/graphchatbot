from enum import StrEnum
from typing import Any, Mapping

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueCompiler, ExpliqueTask
from app.bots.explique.models import (
    MessageEvent,
    Persistence,
    SessionSummary,
    StudentIntent,
    StudentState,
)
from app.bots.explique.transcript import EXPLIQUE_SOURCED_DIALOG
from app.bots.explique.tutor_action import TutorAction
from app.compilation.base import MessageCompilerConfig, ModelChoice, PromptContext
from app.llms.utils import flatten_messages

# Tutor actions that get the plan's `direction` field.
_DIRECTION_ACTIONS = (TutorAction.CHALLENGE_MASTERY,)

# Actions/persistence levels that get a representation switch instead of another reworded question.
_SWITCH_ACTIONS = (TutorAction.PROBE, TutorAction.HINT, TutorAction.CHALLENGE_MISCONCEPTION)
_SWITCH_PERSISTENCE = (Persistence.STUCK, Persistence.STALLED)


class ConversationView(StrEnum):
    """Which view of the conversation trails the system prompt. `SOURCED`
    includes retrieved chunks, while `DIALOG` excludes them."""

    SOURCED = "sourced"
    DIALOG = "dialog"


class ResponseContext(PromptContext):
    messages: tuple[BaseMessage, ...]


class SummaryResponseContext(ResponseContext):
    session_summary: SessionSummary


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


class ResponseCompiler(ExpliqueCompiler):
    """Base for the responders: a system prompt, then the conversation, then
    whatever applies only to this turn."""

    conversation_view = ConversationView.SOURCED

    @classmethod
    def build_context(cls, bot: Bot, state: Mapping[str, Any]) -> ResponseContext:
        return ResponseContext(messages=cls.history(bot, state))

    @classmethod
    def compile_messages(cls, bot: Bot, context: ResponseContext) -> list[BaseMessage]:
        """System prompt, then the dialog, then `user_template` if this responder
        closes on one.

        That closing template carries what only this turn knows. Placing it after
        the dialog puts the move right before generation, and keeps
        `system prompt + dialog` a stable prefix the server can cache across turns.
        """
        messages: list[BaseMessage] = [
            SystemMessage(content=cls.render(bot, cls.config.system_template, context)),
            *context.messages,
        ]
        if cls.config.user_template is not None:
            messages.append(HumanMessage(content=cls.render(bot, cls.config.user_template, context)))
        return messages

    @classmethod
    def history(cls, bot: Bot, state: Mapping[str, Any]) -> tuple[BaseMessage, ...]:
        """This compiler's view of the conversation, with multi-part content
        flattened so it can be forwarded straight into a call."""
        view = bot.dialog if cls.conversation_view is ConversationView.DIALOG else EXPLIQUE_SOURCED_DIALOG
        return tuple(flatten_messages(view.messages(state["messages"])))


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
    `nodes/transcribe_image.py`.

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
    """The closing recap. Keeps the retrieved material because this is the one
    reply that cites sources, and it is built from the session digest rather than
    from a re-reading of the last few turns."""

    config = response_config(overrides=(StudentIntent.END_SESSION,), system_template="intent-end.md")

    @classmethod
    def build_context(cls, bot: Bot, state: Mapping[str, Any]) -> SummaryResponseContext:
        return SummaryResponseContext(
            messages=cls.history(bot, state),
            session_summary=state.get("session_summary") or SessionSummary(),
        )


class PracticeUnavailableResponseCompiler(ResponseCompiler):
    """The apology for a practice request the practice node could not fill.

    A practice request that *was* filled never reaches a compiler: the rendered
    quiz is returned verbatim, with no model call at all.
    """

    config = response_config(
        overrides=(StudentIntent.REQUEST_PRACTICE,),
        system_template="intent-practice-unavailable.md",
    )
    conversation_view = ConversationView.DIALOG


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
    conversation_view = ConversationView.DIALOG

    @classmethod
    def build_context(cls, bot: Bot, state: Mapping[str, Any]) -> TutoringResponseContext:
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

        return TutoringResponseContext(
            messages=cls.history(bot, state),
            student_state=student_state,
            tutor_action=tutor_action,
            action_template=f"action-{tutor_action}.md",
            plan_directive=plan_directive,
            points_tested=points_tested,
            switch_representation=switch_representation,
        )
