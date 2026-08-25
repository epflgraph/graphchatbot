from app.bots.compilers.base import BotTask
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.compilation.dialog import DialogTurnsCompiler


class ResponseCompiler(DialogTurnsCompiler):
    """The reply: the bot's own system prompt, then the conversation it answers to.

    Shared by every family whose reply needs nothing but the conversation. Each
    ships its own `prompt.md`, which is what makes one class enough; a family
    that leads with more than one prompt subclasses this to name the other.
    """

    config = MessageCompilerConfig(
        task=BotTask.RESPOND,
        model_choice=ModelChoice.MAIN,
        system_template="prompt.md",
    )
