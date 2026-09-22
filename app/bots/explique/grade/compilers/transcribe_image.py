from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.transcribe_image import ImageTranscriptionCompiler
from app.bots.explique.grade.transcript import replace_attachments


class GradeImageTranscriptionCompiler(ImageTranscriptionCompiler):
    """Transcribes the image in the latest turn, never reading an attached file's text with it."""

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        last_turn = replace_attachments(state["original_messages"][-1], "")
        return super().context_fields(bot, {**state, "original_messages": [last_turn]})
