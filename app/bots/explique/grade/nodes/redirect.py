from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.models import GradeStudentIntent
from app.bots.explique.grade.prompts import JAILBREAK_TEMPLATE, REDIRECT_TEMPLATE
from app.bots.explique.grade.state import GradeBotState
from app.bots.utils import stream_text
from app.compilation.templates import render_prompt


async def redirect_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Answer a turn that is not an explanation: one off the locked topic is pointed back
    at it, one that instructs the grader is told it counts for nothing."""
    bot = runtime.context
    template = JAILBREAK_TEMPLATE if state["category"] == GradeStudentIntent.JAILBREAK else REDIRECT_TEMPLATE
    redirect = render_prompt(
        bot.prompt_search_path, template, topic=state["topic_lock"].topic, lang_code=state.get("lang_code")
    )
    await stream_text(redirect, runtime.stream_writer)
    return {"messages": [AIMessage(content=redirect)]}
