from typing import Any, Mapping

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.bots.base import Bot
from app.bots.explique.compilers.base import DialogContext, ExpliqueCompiler, ExpliqueTask
from app.bots.explique.transcript import last_tool_messages
from app.compilation.base import MessageCompilerConfig, ModelChoice


class RetrieveContext(DialogContext):
    prior_retrieval: tuple[BaseMessage, ...]


class RetrieveCompiler(ExpliqueCompiler):
    """No `output_schema`: this call answers with a `search_course_material`
    tool call, or with nothing at all when the dialog already holds what the
    tutor needs. The tools it may call are bound by the node, which owns them.

    Overrides `build_context`/`compile_messages` instead of `DialogCompiler`'s:
    prior tool calls and results need to stay as real messages, not get
    folded into the stringified dialog."""

    config = MessageCompilerConfig(
        task=ExpliqueTask.RETRIEVE,
        model_choice=ModelChoice.LIGHT,
        system_template="retrieve-sys.md",
        user_template="retrieve-usr.md",
    )

    @classmethod
    def build_context(cls, bot: Bot, state: Mapping[str, Any]) -> RetrieveContext:
        return RetrieveContext(
            dialog_history=cls.dialog_history(bot, state),
            prior_retrieval=last_tool_messages(state["messages"]),
        )

    @classmethod
    def compile_messages(cls, bot: Bot, context: RetrieveContext) -> list[BaseMessage]:
        messages = [SystemMessage(content=cls.render(bot, cls.config.system_template, context))]
        messages.extend(context.prior_retrieval)
        if cls.config.user_template is not None:
            messages.append(HumanMessage(content=cls.render(bot, cls.config.user_template, context)))
        return messages
