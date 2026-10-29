from enum import StrEnum

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BotState
from app.bots.callbacks.base import ModelCallbacks, ToolRoundCallbacks
from app.bots.callbacks.dedupe import dedupe_tool_results
from app.bots.callbacks.status import announce_status
from app.bots.compilers.classify import ClassifyCompiler
from app.bots.course.compilers.retrieve import RetrieveCompiler
from app.bots.course.course_bot import CourseBot, RequestType
from app.bots.course.direct.compilers import DirectResponseCompiler
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node


class Node(StrEnum):
    """Graph node identifiers for the direct course bot."""

    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    TOOLS = "tools"
    RESPOND = "respond"


class DirectCourseBot(CourseBot):
    """CourseBot variant that gives direct, complete answers.

    The graph is split into a lightweight retrieval node that decides what to
    search, and a separate answer node that produces the final reply from the
    retrieved sources. No language detection or enforcement is performed; the
    answer model chooses the reply language from context.
    """

    MAX_RETRIEVAL_ROUNDS = 1

    model_nodes = (Node.RESPOND,)

    def _route_after_classify(self, state: BotState) -> Node:
        """Course-content requests retrieve material; everything else answers directly."""
        category = state.get("category")
        if self.CATEGORIES[category]["tool_choice"] is None:
            return Node.RESPOND
        return Node.RETRIEVE

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)
        workflow.add_node(
            Node.CLASSIFY,
            make_classify_node(self.CATEGORIES, fallback=RequestType.GREETING, compiler=ClassifyCompiler),
        )
        retrieve_node = make_model_node(
            tools,
            name=Node.RETRIEVE,
            compiler=RetrieveCompiler,
            on_text=Node.RESPOND,
            on_tools=Node.TOOLS,
            text_is_reply=False,
            max_tool_rounds=self.MAX_RETRIEVAL_ROUNDS,
            model_callbacks=ModelCallbacks(before=(announce_status,)),
        )
        workflow.add_node(retrieve_node.name, retrieve_node)
        workflow.add_node(
            Node.TOOLS, make_tools_node(tools, tool_round_callbacks=ToolRoundCallbacks(after=(dedupe_tool_results,)))
        )
        respond_node = make_model_node(
            [],
            name=Node.RESPOND,
            compiler=DirectResponseCompiler,
            model_callbacks=ModelCallbacks(before=(announce_status,)),
        )
        workflow.add_node(respond_node.name, respond_node)

        workflow.set_entry_point(Node.CLASSIFY)
        workflow.add_conditional_edges(Node.CLASSIFY, self._route_after_classify)

        return workflow.compile()
