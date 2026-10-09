from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueTextCompiler
from app.bots.explique.grade.compilers.base import GradeCompiler, GradeDialogTextContext, GradeTask
from app.bots.explique.grade.models import Revision
from app.compilation.base import MessageCompilerConfig, ModelChoice


class GradeRevisionContext(GradeDialogTextContext):
    lang_code: str | None


class GradeRevisionCompiler(GradeCompiler, ExpliqueTextCompiler):
    config = MessageCompilerConfig(
        task=GradeTask.REVISION,
        system_template="revision-sys.md",
        user_template="revision-usr.md",
        model_choice=ModelChoice.LIGHT,
        output_schema=Revision,
    )
    context_class = GradeRevisionContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"lang_code": state.get("lang_code")}
