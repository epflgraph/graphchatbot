import logging
from typing import Optional

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BotState
from app.bots.course.course_bot import CourseBot
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.gate import make_gate_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node

logger = logging.getLogger(__name__)

STAGES = ['no_case_study', 'no_position', 'early', 'mid', 'late', 'ended']

STAGE_CATEGORIES = {
    'early': {'description': "The debate is in an early stage: most ideas have not yet been exchanged or developed."},
    'mid':   {'description': "The debate is in an intermediate stage: some ideas have been developed, but there is more to discuss."},
    'late':  {'description': "The debate is in a late stage: most ideas have been discussed and there is little left to explore."},
}


class DebateCourseBotState(BotState):
    active_node: Optional[str]


class DebateCourseBot(CourseBot):
    """CourseBot variant that uses a peer-debate pedagogical style."""

    model_nodes: tuple[str, ...] = tuple(f'model_{stage}' for stage in STAGES)

    STAGE_CATEGORIES: dict = STAGE_CATEGORIES

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(DebateCourseBotState, context_schema=Bot)

        workflow.add_node('gate_case_study', make_gate_node(
            question="Is it clear which case study to discuss at this point in the conversation?",
            if_yes='gate_position',
            if_no='model_no_case_study',
        ))
        workflow.add_node('gate_position', make_gate_node(
            question="Has the student stated which answer options they think are correct or incorrect, or at least started giving some arguments?",
            if_yes='gate_ended',
            if_no='model_no_position',
        ))
        workflow.add_node('gate_ended', make_gate_node(
            question="Has the complete solution to the case study already been explicitly revealed in this conversation?",
            if_yes='model_ended',
            if_no='classify_stage',
        ))

        workflow.add_node('classify_stage', make_classify_node(self.STAGE_CATEGORIES))
        workflow.add_conditional_edges('classify_stage', lambda s: f"model_{s['category']}")

        for stage in STAGES:
            node_name = f'model_{stage}'
            workflow.add_node(node_name, make_model_node(
                tools,
                prompt_name=stage,
                state_update={'active_node': node_name},
            ))

        workflow.add_node('tools', make_tools_node(tools, back_to=None))

        workflow.set_entry_point('gate_case_study')

        return workflow.compile()
