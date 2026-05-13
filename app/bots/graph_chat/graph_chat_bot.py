import logging

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

# TODO move tool functions to graph_chat/tools
from app.agent.tools.nodes import search_nodes
from app.agent.tools.exoset import search_exercises
from app.agent.tools.news import search_news
from app.bots.base import Bot, BotState
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node

logger = logging.getLogger(__name__)

CATEGORIES = {
    'greeting': {
        'description': "Requests that are just a greeting or similar.",
        'tool_choice': None,
    },
    'help-with-assignment': {
        'description': "Requests that present an exercise or question and want help with its solution.",
        'tool_choice': 'search_graph',
    },
    'explain-concept': {
        'description': "Requests that ask a question about some specific concept or domain.",
        'tool_choice': 'search_graph',
    },
    'people': {
        'description': "Requests about researchers or instructors at EPFL.",
        'tool_choice': 'search_graph',
    },
    'lectures': {
        'description': "Requests about EPFL video lectures.",
        'tool_choice': 'search_graph',
    },
    'exercises': {
        'description': "Requests that want to find exercises about some topic.",
        'tool_choice': 'search_exoset',
    },
    'courses': {
        'description': "Requests about EPFL courses.",
        'tool_choice': 'search_graph',
    },
    'study-plan': {
        'description': "Requests about the EPFL study plan, for example about credits, pre-requisites or the availability of courses in a given plan.",
        'tool_choice': 'search_graph',
    },
    'schedule': {
        'description': "Student requests about the time schedule of the classes.",
        'tool_choice': 'search_graph',
    },
    'student-projects': {
        'description': "Explicit requests about student projects.",
        'tool_choice': 'search_graph',
    },
    'internships': {
        'description': "Explicit requests about student internships.",
        'tool_choice': 'search_graph',
    },
    'labs-or-units': {
        'description': "Requests about EPFL units (labs, centers, institutes, chairs, etc.).",
        'tool_choice': 'search_graph',
    },
    'startups': {
        'description': "Explicit requests about EPFL startups or spin-off companies.",
        'tool_choice': 'search_graph',
    },
    'news': {
        'description': "Explicit requests for news articles from EPFL.",
        'tool_choice': 'search_news',
    },
}


class GraphChatBot(Bot):
    name = 'graph-chat'
    groups = None

    CATEGORIES = CATEGORIES

    def build_tools(self) -> list:
        return [
            tool('search_graph')(search_nodes),
            tool('search_news')(search_news),
            tool('search_exoset')(search_exercises),
        ]

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)
        workflow.add_node('classify', make_classify_node(self.CATEGORIES))
        workflow.add_node('model', make_model_node(tools))
        workflow.add_node('tools', make_tools_node(tools, back_to='model'))
        workflow.set_entry_point('classify')
        workflow.add_edge('classify', 'model')

        return workflow.compile()
