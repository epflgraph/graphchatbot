import logging
from enum import StrEnum

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BotState
from app.bots.compilers.classify import ClassifyCompiler
from app.bots.compilers.respond import ResponseCompiler
from app.bots.graph_chat.graph_chat_tools import search_exoset, search_graph, search_news
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node

logger = logging.getLogger(__name__)


class RequestType(StrEnum):
    GREETING = "greeting"
    HELP_WITH_ASSIGNMENT = "help-with-assignment"
    EXPLAIN_CONCEPT = "explain-concept"
    PEOPLE = "people"
    LECTURES = "lectures"
    EXERCISES = "exercises"
    COURSES = "courses"
    STUDY_PLAN = "study-plan"
    SCHEDULE = "schedule"
    STUDENT_PROJECTS = "student-projects"
    INTERNSHIPS = "internships"
    LABS_OR_UNITS = "labs-or-units"
    STARTUPS = "startups"
    NEWS = "news"


CATEGORIES = {
    RequestType.GREETING: {
        "description": "Requests that are just a greeting or similar.",
        "tool_choice": None,
    },
    RequestType.HELP_WITH_ASSIGNMENT: {
        "description": "Requests that present an exercise or question and want help with its solution.",
        "tool_choice": "search_graph",
    },
    RequestType.EXPLAIN_CONCEPT: {
        "description": "Requests that ask a question about some specific concept or domain.",
        "tool_choice": "search_graph",
    },
    RequestType.PEOPLE: {
        "description": "Requests about researchers or instructors at EPFL.",
        "tool_choice": "search_graph",
    },
    RequestType.LECTURES: {
        "description": "Requests about EPFL video lectures.",
        "tool_choice": "search_graph",
    },
    RequestType.EXERCISES: {
        "description": "Requests that want to find exercises about some topic.",
        "tool_choice": "search_exoset",
    },
    RequestType.COURSES: {
        "description": "Requests about EPFL courses.",
        "tool_choice": "search_graph",
    },
    RequestType.STUDY_PLAN: {
        "description": "Requests about the EPFL study plan, for example about credits, pre-requisites or the availability of courses in a given plan.",
        "tool_choice": "search_graph",
    },
    RequestType.SCHEDULE: {
        "description": "Student requests about the time schedule of the classes.",
        "tool_choice": "search_graph",
    },
    RequestType.STUDENT_PROJECTS: {
        "description": "Explicit requests about student projects.",
        "tool_choice": "search_graph",
    },
    RequestType.INTERNSHIPS: {
        "description": "Explicit requests about student internships.",
        "tool_choice": "search_graph",
    },
    RequestType.LABS_OR_UNITS: {
        "description": "Requests about EPFL units (labs, centers, institutes, chairs, etc.).",
        "tool_choice": "search_graph",
    },
    RequestType.STARTUPS: {
        "description": "Explicit requests about EPFL startups or spin-off companies.",
        "tool_choice": "search_graph",
    },
    RequestType.NEWS: {
        "description": "Explicit requests for news articles from EPFL.",
        "tool_choice": "search_news",
    },
}


class GraphChatBot(Bot):
    name = "graph-chat"
    groups = []

    CATEGORIES = CATEGORIES

    def prompt_context(self) -> dict:
        return super().prompt_context() | {"categories": self.CATEGORIES}

    def build_tools(self) -> list:
        return [
            tool("search_graph")(search_graph),
            tool("search_news")(search_news),
            tool("search_exoset")(search_exoset),
        ]

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)
        workflow.add_node(
            "classify",
            make_classify_node(self.CATEGORIES, fallback=RequestType.GREETING, compiler=ClassifyCompiler),
        )
        workflow.add_node("model", make_model_node(tools, compiler=ResponseCompiler))
        workflow.add_node("tools", make_tools_node(tools))
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "model")

        return workflow.compile()
