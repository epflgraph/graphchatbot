from app.bots.compilers.grounded import GroundedDialogCompiler
from app.bots.explique.transcript import summarize_quiz
from app.bots.transcript import keep_dialog_roles
from app.compilation.base import MessageCompiler, Task
from app.compilation.dialog import DialogTextCompiler, DialogTurnsCompiler
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


class ExpliqueCompiler(MessageCompiler):
    message_callbacks = (keep_dialog_roles, summarize_quiz, flatten_message)


class ExpliqueTextCompiler(ExpliqueCompiler, DialogTextCompiler):
    """The conversation quoted into the prompt."""


class ExpliqueTurnsCompiler(ExpliqueCompiler, DialogTurnsCompiler):
    """The conversation trailing the prompt as real turns."""


class ExpliqueGroundedCompiler(ExpliqueCompiler, GroundedDialogCompiler):
    """The conversation that also includes retrieval results."""
