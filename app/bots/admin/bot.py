from abc import abstractmethod
from typing import Optional

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BaseState
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.interfaces.graphai import GraphAIClient


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
        bot_introduction: str   — opening paragraph(s) for the system prompt

    Subclasses may override:
        CATEGORIES              — to customise classification categories
        unrelated_note: str     — extra bullet appended to general considerations
        build_tools()           — to add more tools or change tool logic entirely
        build_graph()           — to change the graph topology
    """

    tool_name: str
    tool_description: str

    CATEGORIES: dict = CATEGORIES

    _admin_format = """\
* Lay out urls as Markdown links.
* The result should be a mix between text and Markdown links in a Wikipedia fashion.
* Mix in the relevant resources from the tools in your response as Markdown links in-between the explanation, instead of everything at the end.
* Include at least 5 inline links to resources in your answer.
* Do not use words or phrases that express doubt or provide a subjective opinion."""

    _admin_behavior = """\
* Be proactive and helpful when you answer: Give specific suggestions about what you can do next in relation with your response.
* Never alter the information from the source documents. Copy fields exactly as they are.
* Use Markdown links often. As their text, avoid placeholder words like "here" or "this link".
* If the tools cannot provide an answer to the request, or they return an error, then just apologize and ask the user to rephrase their query.
* If the request is subjective, do not use any tool. Instead, ask the user to rephrase it in an objective way."""

    @property
    @abstractmethod
    def bot_introduction(self) -> str: ...

    @property
    def unrelated_note(self) -> str:
        return ""

    @property
    def system_prompt(self) -> str:
        from app.bots.prompts import general_considerations

        behavior = self._admin_behavior
        if note := self.unrelated_note:
            behavior += f'\n{note}'
        behavior += f'\n{general_considerations()}'

        return '\n\n'.join([
            self.bot_introduction,
            f'# Format\n{self._admin_format}',
            f'# General considerations\n{behavior}',
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
