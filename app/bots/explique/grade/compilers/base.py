from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueCompiler, GroundedDialogContext
from app.bots.explique.grade.transcript import graded_turns, without_attachments
from app.compilation.base import PromptContext, Task
from app.compilation.dialog import DialogTextContext


class GradeTask(Task):
    """The tasks only the grader runs, on top of the `ExpliqueTask` ones."""

    DERIVE_POINTS = "derive-points"
    FEEDBACK = "feedback"


class GradeContext(PromptContext):
    """What every grade call carries: the topic the session committed to, and the points it has to cover."""

    locked_topic: str
    # Empty while the points are still being derived.
    topic_points: tuple[str, ...] = ()


class GradeDialogTextContext(DialogTextContext, GradeContext):
    """The conversation quoted in, plus what every grade call carries."""


class GradeGroundedDialogContext(GroundedDialogContext, GradeContext):
    """The conversation quoted in with its sources, plus what every grade call carries."""


class GradeCompiler(ExpliqueCompiler):
    """Base for the grader's compilers: every call knows which topic the session is on."""

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {
            "locked_topic": state["topic_lock"].topic.name,
            "topic_points": state.get("topic_points") or (),
        }


class GradedTurnsCompiler(GradeCompiler):
    """The conversation as the grader flavor reads it:
    - Attached files are replaced by a placeholder
    - Jailbreak attempts and their replies are omitted"""

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        search_path = bot.prompt_search_path
        messages = without_attachments(search_path, state["messages"])
        graded = graded_turns(search_path, state["topic_lock"].topic, messages)
        return super().context_fields(bot, {**state, "messages": graded})
