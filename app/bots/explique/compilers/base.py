from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.transcript import last_tool_results
from app.compilation.base import Task
from app.compilation.dialog import DialogTextCompiler, DialogTextContext


class ExpliqueTask(Task):
    """The tutor's tasks, each one with its own compiler."""

    TRANSCRIBE_IMAGE = "transcribe-image"
    DETECT_LANGUAGE = "detect-language"
    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    EVALUATE = "evaluate"
    PLAN_CHALLENGE = "plan-challenge"
    PRACTICE = "practice"
    SUMMARIZE = "summarize"
    RESPOND = "respond"


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
        was none. Collected separately since tool messages skip the compiled
        dialog."""
        return last_tool_results(state["messages"])
