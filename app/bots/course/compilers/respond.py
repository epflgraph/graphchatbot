from typing import Any, Mapping

from app.bots.base import Bot
from app.bots.compilers.respond import ResponseCompiler
from app.bots.transcript import keep_dialog_roles, last_tool_results
from app.compilation.dialog import DialogTurnsContext


class GroundedResponseContext(DialogTurnsContext):
    """Context for a course answer that also needs this turn's retrieved material."""

    sources: str


class GroundedResponseCompiler(ResponseCompiler):
    """The reply, backed by a sources block instead of raw tool turns.

    The conversation is first stripped of tool-call and tool-result messages by
    `keep_dialog_roles`, then the retrieved material is injected as a `<sources>`
    block in the prompt context.
    """

    config = ResponseCompiler.config.model_copy(update={"system_template": "respond-sys.md"})
    context_class = GroundedResponseContext
    message_callbacks = (keep_dialog_roles,)

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"sources": last_tool_results(state["original_messages"])}
