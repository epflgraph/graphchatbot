from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.prompts import DECLINE_TOPIC_TEMPLATE
from app.bots.explique.grade.state import GradeBotState
from app.bots.utils import stream_text
from app.compilation.templates import render_prompt


async def decline_topic_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Tell the student the topic they picked cannot be explained yet: it has no points to grade against."""
    bot = runtime.context
    reply = render_prompt(
        bot.prompt_search_path,
        DECLINE_TOPIC_TEMPLATE,
        topic=state["topic_lock"].topic,
        lang_code=state.get("lang_code"),
    )
    await stream_text(reply, runtime.stream_writer)
    return {"messages": [AIMessage(content=reply)]}
