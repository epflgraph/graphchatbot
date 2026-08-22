from app.bots.explique.train.compilers.base import ExpliqueTask, ExpliqueTextCompiler
from app.compilation.base import MessageCompilerConfig, ModelChoice


class RetrieveCompiler(ExpliqueTextCompiler):
    """No `output_schema`: this call answers with a `search_course_material`
    tool call, or with nothing at all when the dialog already holds what the
    tutor needs. The tools it may call are bound by the node, which owns them."""

    config = MessageCompilerConfig(
        task=ExpliqueTask.RETRIEVE,
        model_choice=ModelChoice.LIGHT,
        system_template="retrieve-sys.md",
        user_template="retrieve-usr.md",
    )
