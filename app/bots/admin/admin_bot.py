import logging

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot, BotState
from app.bots.compilers.classify import ClassifyCompiler
from app.bots.compilers.respond import ResponseCompiler
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.compilation.templates import render_prompt
from app.interfaces.graphai import graphai

logger = logging.getLogger(__name__)


CATEGORIES = {
    "greeting": {
        "description": "The user is just greeting the assistant or similar.",
        "tool_choice": None,
    },
    "main": {
        "description": "The user has a substantive request within the bot's domain.",
        "tool_choice": "any",
    },
    "unrelated": {
        "description": "The user's request is completely unrelated to the bot's domain.",
        "tool_choice": None,
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
        prompts/prompt.md       — the system prompt `ResponseCompiler` leads with

    Subclasses may override:
        CATEGORIES              — to customise classification categories
        build_tools()           — to add more tools or change tool logic entirely
        build_graph()           — to change the graph topology
    """

    tool_name: str

    CATEGORIES: dict = CATEGORIES

    def prompt_context(self) -> dict:
        return super().prompt_context() | {"categories": self.CATEGORIES}

    async def _search(self, query: str) -> list[dict]:
        logger.info(f"Called `{self.tool_name}`")
        result = await graphai.rag_retrieve(index=self.index, texts=[query])
        logger.info(f"Retrieved {len(result.chunks)} chunks.")
        return [chunk.to_dict() for chunk in result.chunks]

    def build_tools(self) -> list:
        description = render_prompt(self.prompt_search_path, "tool-description.md", **self.prompt_context())
        return [tool(self.tool_name, description=description)(self._search)]

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)
        workflow.add_node(
            "classify", make_classify_node(self.CATEGORIES, fallback="greeting", compiler=ClassifyCompiler)
        )
        workflow.add_node("model", make_model_node(tools, compiler=ResponseCompiler))
        workflow.add_node("tools", make_tools_node(tools))
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "model")

        return workflow.compile()
