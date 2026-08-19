from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueTask, GroundedDialogCompiler, GroundedDialogContext
from app.bots.explique.models import PracticeMaterial
from app.compilation.base import MessageCompilerConfig, ModelChoice


class PracticeContext(GroundedDialogContext):
    """The quiz needs to be written in the student's language."""

    lang_code: str | None


class PracticeCompiler(GroundedDialogCompiler):
    config = MessageCompilerConfig(
        task=ExpliqueTask.PRACTICE,
        model_choice=ModelChoice.LIGHT,
        system_template="practice-sys.md",
        user_template="practice-usr.md",
        output_schema=PracticeMaterial,
    )

    @classmethod
    def build_context(cls, bot: Bot, state: Mapping[str, Any]) -> PracticeContext:
        return PracticeContext(
            dialog_history=cls.dialog_history(bot, state),
            sources=cls.sources(state),
            lang_code=state.get("lang_code"),
        )
