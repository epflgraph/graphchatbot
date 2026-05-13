import inspect
import logging
from pathlib import Path

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BotState, BOTS_ROOT
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.bots.prompts import resolve
from app.interfaces.graphai import graphai

logger = logging.getLogger(__name__)


CATEGORIES = {
    'greeting': {
        'description': "The user is just greeting the assistant or similar.",
        'force_tools': False,
    },
    'main': {
        'description': "The user has a substantive request within the bot's domain.",
        'force_tools': True,
    },
    'unrelated': {
        'description': "The user's request is completely unrelated to the bot's domain.",
        'force_tools': False,
    },
}


class AdminBot(Bot):
    """
    Abstract base for classified single-domain RAG bots.

    Subclasses must define:
        name: str
        index: str
        groups: list[str]
        tool_name: str          — name of the search tool exposed to the LLM
        prompt.md               — full system prompt template (auto-resolved at class creation)

    Subclasses may override:
        CATEGORIES              — to customise classification categories
        build_tools()           — to add more tools or change tool logic entirely
        build_graph()           — to change the graph topology
    """

    tool_name: str

    CATEGORIES: dict = CATEGORIES

    async def _search(self, query: str) -> list:
        logger.info(f"Called `{self.tool_name}` with query=`{query}`")
        results = await graphai.rag_retrieve(index=self.index, texts=[query])
        logger.info(f"Retrieved {len(results)} chunks.")
        return results

    def build_tools(self) -> list:
        subclass_dir = Path(inspect.getfile(type(self))).parent
        description = resolve('tool_description', subclass_dir, BOTS_ROOT)
        return [tool(self.tool_name, description=description)(self._search)]

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)
        workflow.add_node('classify', make_classify_node(self.CATEGORIES))
        workflow.add_node('model', make_model_node(tools))
        workflow.add_node('tools', make_tools_node(tools, back_to='model'))
        workflow.set_entry_point('classify')
        workflow.add_edge('classify', 'model')

        return workflow.compile()
