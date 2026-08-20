import logging

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BotState
from app.bots.course.course_bot import CourseBot
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node

logger = logging.getLogger(__name__)

CATEGORIES = {
    "no-case-study": {
        "description": "The student has not yet indicated which case study they want to discuss.",
        "tool_choice": "any",
    },
    "no-position": {
        "description": "A case study has been chosen but the student has not yet stated which answer options they think are correct or incorrect, nor started giving arguments.",
        "tool_choice": "any",
    },
    "early-stage-debate": {
        "description": "The debate is in an early stage: most ideas have not yet been exchanged or developed.",
        "tool_choice": "any",
    },
    "mid-stage-debate": {
        "description": "The debate is in an intermediate stage: some ideas have been developed, but there is more to discuss.",
        "tool_choice": "any",
    },
    "late-stage-debate": {
        "description": "The debate is in a late stage: most ideas have been discussed and there is little left to explore.",
        "tool_choice": "any",
    },
    "debate-ended": {
        "description": "The complete solution to the case study has already been explicitly revealed in this conversation.",
        "tool_choice": "any",
    },
}


class DebateCourseBot(CourseBot):
    """CourseBot variant that uses a peer-debate pedagogical style."""

    model_nodes: tuple[str, ...] = tuple(f"model-{c}" for c in CATEGORIES)

    CATEGORIES: dict = CATEGORIES

    # A debate opens on the case-study choice, not on a generic `prompt.md`.
    DEFAULT_PROMPT_NAME = "prompt-no-case-study"

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)

        workflow.add_node("classify", make_classify_node(self.CATEGORIES, fallback="no-case-study"))
        workflow.add_conditional_edges("classify", lambda s: f"model-{s['category']}")

        for category in self.CATEGORIES:
            workflow.add_node(f"model-{category}", make_model_node(tools, prompt_name=f"prompt-{category}"))

        workflow.add_node("tools", make_tools_node(tools))

        workflow.set_entry_point("classify")

        return workflow.compile()
