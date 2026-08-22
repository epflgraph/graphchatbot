from app.bots.explique.train.compilers.base import ExpliqueGroundedCompiler, ExpliqueTask
from app.bots.explique.train.models import StudentState
from app.compilation.base import MessageCompilerConfig, ModelChoice


class EvaluateCompiler(ExpliqueGroundedCompiler):
    config = MessageCompilerConfig(
        task=ExpliqueTask.EVALUATE,
        model_choice=ModelChoice.LIGHT,
        system_template="evaluate-sys.md",
        user_template="evaluate-usr.md",
        output_schema=StudentState,
    )
