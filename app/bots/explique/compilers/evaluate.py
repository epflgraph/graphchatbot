from app.bots.explique.compilers.base import ExpliqueTask, GroundedDialogCompiler
from app.bots.explique.models import StudentState
from app.compilation.base import MessageCompilerConfig, ModelChoice


class EvaluateCompiler(GroundedDialogCompiler):
    config = MessageCompilerConfig(
        task=ExpliqueTask.EVALUATE,
        model_choice=ModelChoice.LIGHT,
        system_template="evaluate-sys.md",
        user_template="evaluate-usr.md",
        output_schema=StudentState,
    )
