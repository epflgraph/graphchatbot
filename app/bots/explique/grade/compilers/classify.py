from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.classify import ClassifyCompiler
from app.bots.explique.grade.compilers.base import GradeDialogTextContext, GradedTurnsCompiler
from app.bots.explique.grade.transcript import graded_turns
from app.llms.utils import flatten_content, stringify_messages


class GradeClassifyContext(GradeDialogTextContext):
    """The conversation prior to student's last message, and that message itself."""

    last_student_message: str


class GradeClassifyCompiler(GradedTurnsCompiler, ClassifyCompiler):
    """The tutor's classifier, reading past the jailbreak turns: an explanation
    sent again after one is an explanation, not a second attempt."""

    context_class = GradeClassifyContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        *prior, last = graded_turns(bot.prompt_search_path, state["topic_lock"].topic, state["messages"])
        return super().context_fields(bot, state) | {
            "dialog_history": stringify_messages(prior),
            "last_student_message": flatten_content(last.content),
        }
