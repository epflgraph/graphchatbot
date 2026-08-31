import logging
from enum import StrEnum

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.bots.base import Bot, BotState
from app.bots.compilers.classify import ClassifyCompiler
from app.bots.course.compilers.retrieve import RetrieveCompiler
from app.bots.course.course_bot import CourseBot, RequestType
from app.bots.course.hinting.artifacts import HintingResponseArtifact
from app.bots.course.hinting.compilers import HintingPlainTextCompiler, HintingResponseCompiler
from app.bots.course.hinting.models import Hint, HintingResponse, Solution
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.compilation.invoke import structured_call, text_call

logger = logging.getLogger(__name__)


class Node(StrEnum):
    """Graph node identifiers for the hinting course bot."""

    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    TOOLS = "tools"
    RESPOND = "respond"


class HintingCourseBot(CourseBot):
    """CourseBot variant that gives Socratic, hint-based guidance.

    The graph is split into a lightweight retrieval node and a single answer
    node. The answer node inspects the request category and either returns a
    plain-text reply (greetings, admin, unrelated, immediate factual questions)
    or a structured hint/solution rendered as HTML (theory/practice). No
    language detection or enforcement is performed.
    """

    MAX_RETRIEVAL_ROUNDS = 1

    include_solution: bool = False

    model_nodes = (Node.RESPOND,)

    @staticmethod
    def _route_after_classify(state: BotState) -> Node:
        """Course-content requests retrieve material; everything else answers directly."""
        category = state.get("category")
        if category in (RequestType.GREETING, RequestType.ADMIN, RequestType.UNRELATED):
            return Node.RESPOND
        return Node.RETRIEVE

    @staticmethod
    def _fallback_response() -> HintingResponse:
        """What to render when the structured hinting call fails."""
        return HintingResponse(
            opening="Je n'ai pas pu préparer les indices pour cette question.",
            hints=[
                Hint(title="Indice", body="Essaye de reformuler ta question ou de poser une question plus précise.")
            ],
            solution=Solution(title="Réponse complète", body="Désolé, une erreur est survenue. Réessaie plus tard."),
        )

    def _make_respond_node(self):
        """Returns a node that answers according to the request category."""

        async def respond_node(state: BotState, runtime: Runtime[Bot]) -> Command:
            bot = runtime.context
            category = state.get("category")

            if category in (RequestType.GREETING, RequestType.ADMIN, RequestType.UNRELATED, RequestType.IMMEDIATE):
                answer = await text_call(bot, HintingPlainTextCompiler, state)
                return Command(goto=END, update={"messages": [AIMessage(content=answer)]})

            response = await structured_call(
                bot,
                HintingResponseCompiler,
                state,
                fallback=self._fallback_response(),
            )
            html = HintingResponseArtifact(
                course_name=bot.course_name,
                response=response,
                include_solution=bot.include_solution,
            ).render()
            return Command(goto=END, update={"messages": [AIMessage(content=html)]})

        return respond_node

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)
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
            ),
        )
        workflow.add_node(Node.TOOLS, make_tools_node(tools))
        workflow.add_node(Node.RESPOND, self._make_respond_node())

        workflow.set_entry_point(Node.CLASSIFY)
        workflow.add_conditional_edges(Node.CLASSIFY, self._route_after_classify)

        return workflow.compile()
