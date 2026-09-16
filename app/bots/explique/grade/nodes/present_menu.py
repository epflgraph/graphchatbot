import logging

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.prompts import MENU_TEMPLATES, MENU_UNAVAILABLE_TEMPLATE
from app.bots.explique.grade.state import GradeBotState
from app.bots.explique.transcript import all_assistant_turns
from app.bots.utils import stream_text
from app.compilation.templates import render_prompt

logger = logging.getLogger(__name__)


async def present_menu_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Ask for a topic, more insistently each time the student doesn't comply."""
    menu_template = MENU_UNAVAILABLE_TEMPLATE
    topics = state["topics"]
    if topics:
        num_assistant_turns = len(all_assistant_turns(state["messages"]))
        menu_template = MENU_TEMPLATES[min(num_assistant_turns, len(MENU_TEMPLATES) - 1)]

    logger.info("Presenting menu template: %s", menu_template)
    menu = render_prompt(
        runtime.context.prompt_search_path, menu_template, topics=topics, lang_code=state.get("lang_code")
    )
    await stream_text(menu, runtime.stream_writer)
    return {"messages": [AIMessage(content=menu)]}
