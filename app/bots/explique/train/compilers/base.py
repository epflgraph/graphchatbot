from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.train.transcript import keep_dialog_roles, last_tool_results, summarize_quiz
from app.compilation.base import MessageCompiler, Task
from app.compilation.dialog import DialogTextCompiler, DialogTextContext, DialogTurnsCompiler
from app.llms.utils import flatten_message


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
        was none. Read off the original messages, since a callback that drops
        tool turns would take these with them."""
        return last_tool_results(state["original_messages"])


class ExpliqueCompiler(MessageCompiler):
    message_callbacks = (keep_dialog_roles, summarize_quiz, flatten_message)


class ExpliqueTextCompiler(ExpliqueCompiler, DialogTextCompiler):
    """The conversation quoted into the prompt."""


class ExpliqueTurnsCompiler(ExpliqueCompiler, DialogTurnsCompiler):
    """The conversation trailing the prompt as real turns."""


class ExpliqueGroundedCompiler(ExpliqueCompiler, GroundedDialogCompiler):
    """The conversation that also includes retrieval results."""
