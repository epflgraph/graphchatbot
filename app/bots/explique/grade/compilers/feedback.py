from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.grade.compilers.base import GradeCompiler, GradeContext, GradeTask
from app.bots.explique.models import SessionSummary
from app.compilation.base import MessageCompilerConfig, ModelChoice


class FeedbackContext(GradeContext):
    session_summary: SessionSummary
    lang_code: str | None


class GradeFeedbackCompiler(GradeCompiler):
    """Turns an internal session recap into a closing feedback message the student reads."""

    config = MessageCompilerConfig(
        task=GradeTask.FEEDBACK,
        system_template="feedback-sys.md",
        user_template="feedback-usr.md",
        model_choice=ModelChoice.LIGHT,
    )
    context_class = FeedbackContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {
            "session_summary": state["session_summary"],
            "lang_code": state.get("lang_code"),
        }
