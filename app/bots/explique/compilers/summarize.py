from app.bots.explique.compilers.base import DialogCompiler, ExpliqueTask
from app.bots.explique.models import SessionSummary
from app.compilation.base import MessageCompilerConfig, ModelChoice


class SummarizeCompiler(DialogCompiler):
    """Reads the conversation only: the digest is a faithful account of what was
    said, so this call is deliberately not grounded in retrieved sources."""

    config = MessageCompilerConfig(
        task=ExpliqueTask.SUMMARIZE,
        model_choice=ModelChoice.LIGHT,
        system_template="summarize-sys.md",
        user_template="summarize-usr.md",
        output_schema=SessionSummary,
    )
