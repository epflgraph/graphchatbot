from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.explique.transcript import last_tool_results
from app.compilation.base import MessageCompiler, PromptContext, Task


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


class ExpliqueCompiler(MessageCompiler):
    """Base for every explique compiler."""

    @staticmethod
    def dialog_history(bot: Bot, state: Mapping[str, Any]) -> str:
        """The conversation so far as text, with this bot's transcript callbacks
        applied; tool plumbing dropped, a rendered quiz reduced to the questions
        it asked. Ready to embed straight into a prompt."""
        return bot.dialog.messages_str(state["messages"])

    @staticmethod
    def sources(state: Mapping[str, Any]) -> str:
        """The reference material retrieved this turn, or a stand-in saying there
        was none. Collected separately since tool messages skip the compiled
        dialog."""
        return last_tool_results(state["messages"])


class DialogContext(PromptContext):
    """Context for a call that only needs the conversation."""

    dialog_history: str


class GroundedDialogContext(DialogContext):
    """Context for a call that also needs this turn's retrieved material."""

    sources: str


class DialogCompiler(ExpliqueCompiler):
    """Compiler whose prompt embeds the stringified conversation."""

    @classmethod
    def build_context(cls, bot: Bot, state: Mapping[str, Any]) -> DialogContext:
        return DialogContext(dialog_history=cls.dialog_history(bot, state))


class GroundedDialogCompiler(ExpliqueCompiler):
    """Compiler whose prompt embeds the conversation and the sources retrieved for it"""

    @classmethod
    def build_context(cls, bot: Bot, state: Mapping[str, Any]) -> GroundedDialogContext:
        return GroundedDialogContext(
            dialog_history=cls.dialog_history(bot, state),
            sources=cls.sources(state),
        )
