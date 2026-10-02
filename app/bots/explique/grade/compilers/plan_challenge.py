from app.bots.explique.compilers.base import ExpliqueGroundedCompiler, ExpliqueTask
from app.bots.explique.grade.compilers.base import GradedTurnsCompiler, GradeGroundedDialogContext
from app.bots.explique.grade.models import PointsProgress
from app.compilation.base import MessageCompilerConfig, ModelChoice


class GradePlanChallengeCompiler(GradedTurnsCompiler, ExpliqueGroundedCompiler):
    config = MessageCompilerConfig(
        task=ExpliqueTask.PLAN_CHALLENGE,
        system_template="plan-challenge-sys.md",
        user_template="plan-challenge-usr.md",
        model_choice=ModelChoice.LIGHT,
        output_schema=PointsProgress,
    )
    context_class = GradeGroundedDialogContext
