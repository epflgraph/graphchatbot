from typing import Any, Mapping

from langchain_core.messages import BaseMessage

from app.bots.base import Bot
from app.bots.explique.compilers.base import ExpliqueTask, ExpliqueTextCompiler
from app.bots.explique.transcript import last_tool_messages
from app.compilation.base import MessageCompilerConfig, ModelChoice
from app.compilation.dialog import DialogTextContext


class RetrieveContext(DialogTextContext):
    prior_retrieval: tuple[BaseMessage, ...]


class RetrieveCompiler(ExpliqueTextCompiler):
    """No `output_schema`: this call answers with a `search_course_material`
    tool call, or with nothing at all when the dialog already holds what the
    tutor needs. The tools it may call are bound by the node, which owns them.

    Carries turns of its own on top of the quoted dialog: prior tool calls and
    results need to stay as real messages, not get folded into that quote."""

    context_class = RetrieveContext

    config = MessageCompilerConfig(
        task=ExpliqueTask.RETRIEVE,
        model_choice=ModelChoice.LIGHT,
        system_template="retrieve-sys.md",
        user_template="retrieve-usr.md",
    )

    @classmethod
    def context_fields(cls, bot: Bot, state: Mapping[str, Any]) -> dict[str, Any]:
        return super().context_fields(bot, state) | {"prior_retrieval": last_tool_messages(state["original_messages"])}

    @classmethod
    def embedded_turns(cls, bot: Bot, context: RetrieveContext) -> tuple[BaseMessage, ...]:
        return context.prior_retrieval
