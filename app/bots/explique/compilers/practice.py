from app.bots.explique.compilers.base import ExpliqueTask, GroundedDialogCompiler
from app.bots.explique.models import PracticeMaterial
from app.compilation.base import MessageCompilerConfig, ModelChoice


class PracticeCompiler(GroundedDialogCompiler):
    config = MessageCompilerConfig(
        task=ExpliqueTask.PRACTICE,
        model_choice=ModelChoice.LIGHT,
        system_template="practice-sys.md",
        user_template="practice-usr.md",
        output_schema=PracticeMaterial,
    )
