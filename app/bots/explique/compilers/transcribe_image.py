from typing import Any, Mapping

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.bots.base import Bot
from app.bots.explique.compilers.base import DialogCompiler, ExpliqueTask
from app.bots.nodes.transcribe_image import ImageTranscription
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.llms.utils import wrap_content


class ImageTranscriptionCompiler(DialogCompiler):
    """Overrides `compile`, not `compile_messages`: the human turn appends the
    target message's raw content (text + image) to the rendered template,
    instead of using the template alone."""

    config = MessageCompilerConfig(
        task=ExpliqueTask.TRANSCRIBE_IMAGE,
        model_choice=ModelChoice.VISION,
        system_template="transcribe-image-sys.md",
        user_template="transcribe-image-usr.md",
        output_schema=ImageTranscription,
    )

    @classmethod
    def compile(cls, bot: Bot, state: Mapping[str, Any]) -> list[BaseMessage]:
        context = cls.build_context(bot, state)
        user_prompt = cls.render(bot, cls.config.user_template, context)
        original_parts = wrap_content(state["messages"][-1].content)
        return [
            SystemMessage(content=cls.render(bot, cls.config.system_template, context)),
            HumanMessage(content=[*wrap_content(user_prompt), *original_parts]),
        ]
