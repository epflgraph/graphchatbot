from app.bots.compilers.base import BotTask
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.compilation.dialog import DialogTextCompiler


class ClassifyCompiler(DialogTextCompiler):
    """Classifies the conversation from the descriptions in the bot's own categories.

    No `output_schema`: the answer is one of the category names, so its schema is
    built per call from those names — see `app/bots/nodes/classify.py`.
    """

    config = MessageCompilerConfig(
        task=BotTask.CLASSIFY,
        model_choice=ModelChoice.LIGHT,
        system_template="classify-sys.md",
        user_template="classify-usr.md",
    )
