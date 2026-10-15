from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueGroundedCompiler, ExpliqueTask
from app.bots.explique.grade.compilers.base import GradedTurnsCompiler, GradeGroundedDialogContext
from app.bots.explique.grade.models import PointsProgress
from app.compilation.base import MessageCompilerConfig, ModelChoice


class GradePlanChallengeContext(GradeGroundedDialogContext):
    """The conversation and its sources, plus the points applied on earlier turns."""

    past_points_applied: tuple[str, ...] = ()


class GradePlanChallengeCompiler(GradedTurnsCompiler, ExpliqueGroundedCompiler):
    config = MessageCompilerConfig(
        task=ExpliqueTask.PLAN_CHALLENGE,
        system_template="plan-challenge-sys.md",
        user_template="plan-challenge-usr.md",
        model_choice=ModelChoice.CAREFUL,
        output_schema=PointsProgress,
    )
    context_class = GradePlanChallengeContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"past_points_applied": state.get("past_points_applied", ())}
