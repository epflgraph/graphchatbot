from app.bots.explique.compilers.base import ExpliqueGroundedCompiler, ExpliqueTask
from app.bots.explique.models import ChallengePlan
from app.compilation.base import MessageCompilerConfig, ModelChoice


class PlanChallengeCompiler(ExpliqueGroundedCompiler):
    config = MessageCompilerConfig(
        task=ExpliqueTask.PLAN_CHALLENGE,
        model_choice=ModelChoice.LIGHT,
        system_template="plan-challenge-sys.md",
        user_template="plan-challenge-usr.md",
        output_schema=ChallengePlan,
    )
