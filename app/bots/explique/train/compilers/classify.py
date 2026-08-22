from app.bots.explique.train.compilers.base import ExpliqueTask, ExpliqueTextCompiler
from app.compilation.base import MessageCompilerConfig, ModelChoice


class ClassifyCompiler(ExpliqueTextCompiler):
    """No `output_schema`: the classifier answers with one of the category
    names it was given, so its schema is built per call from those names."""

    config = MessageCompilerConfig(
        task=ExpliqueTask.CLASSIFY,
        model_choice=ModelChoice.LIGHT,
        system_template="classify-sys.md",
        user_template="classify-usr.md",
    )
