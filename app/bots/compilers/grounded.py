from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.transcript import last_tool_results
from app.compilation.dialog import DialogTextCompiler, DialogTextContext


class GroundedDialogContext(DialogTextContext):
    """Context for a call that also needs this turn's retrieved material."""

    sources: str


class GroundedDialogCompiler(DialogTextCompiler):
    """Compiler whose prompt quotes the conversation and the sources retrieved for it."""

    context_class = GroundedDialogContext

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"sources": cls.sources(state)}

    @staticmethod
    def sources(state: Mapping[str, Any]) -> str:
        """The reference material retrieved this turn, or a stand-in saying there
        was none. Read off the original messages, since a callback that drops
        tool turns would take these with them."""
        return last_tool_results(state["original_messages"])
