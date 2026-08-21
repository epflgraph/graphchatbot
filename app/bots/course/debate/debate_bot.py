import logging

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BotState
from app.bots.compilers.classify import ClassifyCompiler
from app.bots.course.course_bot import CourseBot
from app.bots.course.debate.compilers import DebateStage, compiler_for
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node

logger = logging.getLogger(__name__)

CATEGORIES = {
    DebateStage.NO_CASE_STUDY: {
        "description": "The student has not yet indicated which case study they want to discuss.",
        "tool_choice": "any",
    },
    DebateStage.NO_POSITION: {
        "description": "A case study has been chosen but the student has not yet stated which answer options they think are correct or incorrect, nor started giving arguments.",
        "tool_choice": "any",
    },
    DebateStage.EARLY: {
        "description": "The debate is in an early stage: most ideas have not yet been exchanged or developed.",
        "tool_choice": "any",
    },
    DebateStage.MID: {
        "description": "The debate is in an intermediate stage: some ideas have been developed, but there is more to discuss.",
        "tool_choice": "any",
    },
    DebateStage.LATE: {
        "description": "The debate is in a late stage: most ideas have been discussed and there is little left to explore.",
        "tool_choice": "any",
    },
    DebateStage.ENDED: {
        "description": "The complete solution to the case study has already been explicitly revealed in this conversation.",
        "tool_choice": "any",
    },
}


class DebateCourseBot(CourseBot):
    """CourseBot variant that uses a peer-debate pedagogical style."""

    model_nodes: tuple[str, ...] = tuple(f"model-{stage}" for stage in DebateStage)

    CATEGORIES: dict = CATEGORIES

    def build_graph(self) -> CompiledStateGraph:
        """Unlike the other families, the reply is not one node: each stage of the
        debate answers from its own prompt, so `classify` picks the node as well
        as the tool choice."""
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)

        workflow.add_node(
            "classify",
            make_classify_node(self.CATEGORIES, fallback=DebateStage.NO_CASE_STUDY, compiler=ClassifyCompiler),
        )
        workflow.add_conditional_edges("classify", lambda s: f"model-{s['category']}")

        for stage in DebateStage:
            workflow.add_node(f"model-{stage}", make_model_node(tools, compiler=compiler_for(stage)))

        workflow.add_node("tools", make_tools_node(tools))

        workflow.set_entry_point("classify")

        return workflow.compile()
