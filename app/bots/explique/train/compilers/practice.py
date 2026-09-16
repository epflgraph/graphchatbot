from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueGroundedCompiler, GroundedDialogContext
from app.bots.explique.train.models import PracticeMaterial
from app.compilation.base import MessageCompilerConfig, ModelChoice, Task


class TrainTask(Task):
    """The task only the tutor runs, on top of the `ExpliqueTask` ones."""

    PRACTICE = "practice"


class PracticeContext(GroundedDialogContext):
    """The quiz needs to be written in the student's language."""

    lang_code: str | None


class PracticeCompiler(ExpliqueGroundedCompiler):
    context_class = PracticeContext

    config = MessageCompilerConfig(
        task=TrainTask.PRACTICE,
        model_choice=ModelChoice.LIGHT,
        system_template="practice-sys.md",
        user_template="practice-usr.md",
        output_schema=PracticeMaterial,
    )

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"lang_code": state.get("lang_code")}
