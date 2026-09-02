from app.bots.compilers.base import BotTask
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.compilation.dialog import DialogTextCompiler


class RetrieveCompiler(DialogTextCompiler):
    """Decides what course material to retrieve for this turn.

    Runs on the light model with the search tool bound. It either emits one or
    more parallel `search_course_material` calls or returns nothing when the
    conversation already contains what the answer node needs.
    """

    config = MessageCompilerConfig(
        task=BotTask.RETRIEVE,
        model_choice=ModelChoice.LIGHT,
        system_template="retrieve-sys.md",
        user_template="retrieve-usr.md",
    )
