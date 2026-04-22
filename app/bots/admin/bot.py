from pathlib import Path
from typing import Optional

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BaseState
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.bots.prompts import general_considerations, resolve
from app.interfaces.graphai import GraphAIClient

_here = Path(__file__).parent


class AdminState(BaseState):
    category: Optional[str]
    force_tools: bool


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
        tool_description: str   — docstring for the search tool
        prompt.md               — opening paragraph(s) for the system prompt (auto-loaded as bot_introduction)

    Subclasses may override:
        CATEGORIES              — to customise classification categories
        build_tools()           — to add more tools or change tool logic entirely
        build_graph()           — to change the graph topology
    """

    tool_name: str
    tool_description: str

    CATEGORIES: dict = CATEGORIES

    _admin_format = resolve(_here / 'admin_format.md', root=_here)
    _admin_behavior = resolve(_here / 'admin_behavior.md', root=_here)

    @property
    def prompt(self) -> str:
        return '\n\n'.join([
            self.bot_introduction,
            f'# Format\n{self._admin_format}',
            f'# General considerations\n{self._admin_behavior}\n{general_considerations()}',
        ])

    async def _search(self, query: str) -> list:
        print(f"[{self.name.upper()} TOOL]", f"Called `{self.tool_name}` with query=`{query}`")
        results = await GraphAIClient().rag_retrieve(index=self.index, texts=[query])
        print(f"[{self.name.upper()} TOOL]", f"Retrieved {len(results)} chunks.")
        return results

    def build_tools(self) -> list:
        return [tool(self.tool_name, description=self.tool_description)(self._search)]

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(AdminState, context_schema=Bot)
        workflow.add_node('classify', make_classify_node(self.CATEGORIES))
        workflow.add_node('model', make_model_node(tools))
        workflow.add_node('tools', make_tools_node(tools, back_to='model'))
        workflow.set_entry_point('classify')
        workflow.add_edge('classify', 'model')

        return workflow.compile()
