from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.compilers.detect_language import LanguageDetectorCompiler
from app.bots.explique.grade.transcript import without_attachments


class GradeLanguageDetectorCompiler(LanguageDetectorCompiler):
    """Detects the student's language from their own words, never from an attached file."""

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, {**state, "messages": without_attachments(state["messages"], "")})
