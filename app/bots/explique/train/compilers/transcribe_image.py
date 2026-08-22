from typing import Any, Mapping

from langchain_core.messages import BaseMessage, HumanMessage

from app.bots.base import Bot
from app.bots.explique.train.compilers.base import ExpliqueTask, ExpliqueTextCompiler
from app.bots.nodes.transcribe_image import ImageTranscription
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.compilation.dialog import DialogTextContext
from app.llms.utils import wrap_content


class ImageTranscriptionContext(DialogTextContext):
    """Context for a call that also needs the target turn's content as raw parts."""

    original_parts: tuple[dict, ...]


class ImageTranscriptionCompiler(ExpliqueTextCompiler):
    """Transcribes the image in the latest turn to text."""

    context_class = ImageTranscriptionContext

    config = MessageCompilerConfig(
        task=ExpliqueTask.TRANSCRIBE_IMAGE,
        model_choice=ModelChoice.VISION,
        system_template="transcribe-image-sys.md",
        user_template="transcribe-image-usr.md",
        output_schema=ImageTranscription,
    )

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {
            "original_parts": wrap_content(state["original_messages"][-1].content)
        }

    @classmethod
    def closing_turns(cls, bot: Bot, context: ImageTranscriptionContext) -> tuple[BaseMessage, ...]:
        # The turn's own parts trail the rendered task: the model has to see the image itself.
        user_prompt = cls.render(bot, cls.config.user_template, context)
        return (HumanMessage(content=[*wrap_content(user_prompt), *context.original_parts]),)
