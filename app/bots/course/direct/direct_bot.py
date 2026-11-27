from enum import StrEnum

from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BotState
from app.bots.compilers.classify import ClassifyCompiler
from app.bots.compilers.detect_language import LanguageDetectorCompiler
from app.bots.course.compilers.retrieve import RetrieveCompiler
from app.bots.course.course_bot import CourseBot, RequestType
from app.bots.course.direct.compilers import DirectResponseCompiler
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.detect_language import make_detect_language_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node


class Node(StrEnum):
    """Graph node identifiers for the direct course bot."""

    DETECT_LANGUAGE = "detect_language"
    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    TOOLS = "tools"
    RESPOND = "respond"


class DirectCourseBot(CourseBot):
    """CourseBot variant that gives direct, complete answers.

    The graph is split into a lightweight retrieval node that decides what to
    search, and a separate answer node that produces the final reply from the
    retrieved sources, in the language a detection node read off the student's
    latest turn.
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
        workflow.add_node(Node.DETECT_LANGUAGE, make_detect_language_node(LanguageDetectorCompiler))
        workflow.add_node(
            Node.CLASSIFY,
            make_classify_node(self.CATEGORIES, fallback=RequestType.GREETING, compiler=ClassifyCompiler),
        )
        workflow.add_node(
            Node.RETRIEVE,
            make_model_node(
                tools,
                compiler=RetrieveCompiler,
                on_text=Node.RESPOND,
                on_tools=Node.TOOLS,
                text_is_reply=False,
                max_tool_rounds=self.MAX_RETRIEVAL_ROUNDS,
                status_events=True,
            ),
        )
        workflow.add_node(Node.TOOLS, make_tools_node(tools))
        workflow.add_node(
            Node.RESPOND,
            make_model_node([], compiler=DirectResponseCompiler, status_events=True),
        )

        workflow.add_edge(START, Node.DETECT_LANGUAGE)
        workflow.add_edge(START, Node.CLASSIFY)
        workflow.add_conditional_edges(Node.CLASSIFY, self._route_after_classify)

        return workflow.compile()
