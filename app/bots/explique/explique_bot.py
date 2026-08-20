from enum import StrEnum
from functools import cached_property

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot
from app.bots.explique.compilers import COMPILERS
from app.bots.explique.compilers.base import ExpliqueTask
from app.bots.explique.models import MessageEvent, StudentIntent
from app.bots.explique.nodes.evaluate import evaluate_node
from app.bots.explique.nodes.evaluate_response import make_evaluate_response_node
from app.bots.explique.nodes.plan_challenge import plan_challenge_node
from app.bots.explique.nodes.practice import practice_node
from app.bots.explique.nodes.respond import make_respond_node
from app.bots.explique.nodes.retrieve import make_retrieve_node
from app.bots.explique.nodes.select_action import select_action_node
from app.bots.explique.nodes.summarize import summarize_node
from app.bots.explique.retrieval import ToolInput, make_search_tool
from app.bots.explique.state import ExpliqueBotState
from app.bots.explique.transcript import EXPLIQUE_DIALOG
from app.bots.languages import LANGUAGES
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.detect_language import make_detect_language_node
from app.bots.nodes.tools import make_tools_node
from app.bots.nodes.transcribe_image import make_image_transcriber_node
from app.compilation.templates import render_prompt
from app.config import config


class Node(StrEnum):
    """Graph node identifiers in one place, so the edges, routers, factory
    targets, and the streaming filter (`model_nodes`) can't drift apart."""

    TRANSCRIBE_IMAGE = "transcribe_image"
    DETECT_LANGUAGE = "detect_language"
    CLASSIFY = "classify"
    RETRIEVE = "retrieve"
    TOOLS = "tools"
    POST_RETRIEVE = "post_retrieve"
    EVALUATE = "evaluate"
    PLAN_CHALLENGE = "plan_challenge"
    PRACTICE = "practice"
    SELECT_ACTION = "select_action"
    SUMMARIZE = "summarize"
    RESPOND = "respond"
    EVALUATE_RESPONSE = "evaluate_response"


class ExpliqueBot(Bot):
    """
    Abstract base for 'explique' bots.

    Pedagogy: the tutor asks the student to explain concepts in a domain, evaluates each
    explanation against reference material using a structured mental model, and responds
    accordingly (probe, hint, explain, motivate, challenge); the session is recapped
    with citations when the student ends it.

    Subclasses must define:
        - name: str
        - index: str
        - groups: list[str]
    """

    # The search tool's argument schema; override to narrow or extend `ToolInput`'s filters.
    tool_input_schema = ToolInput

    # The two nodes that reach the student: `respond` for a rendered quiz,
    # `evaluate_response` for a checked reply. Neither streams.
    model_nodes = (Node.RESPOND, Node.EVALUATE_RESPONSE)

    # The conversation view prompts read: human/ai turns only, quiz markup summarized.
    dialog = EXPLIQUE_DIALOG

    # Student intent to retrieval policy — how the retrieve node binds its
    # search tool for that intent, and how many rounds it may take.
    INTENT_TOOL_CHOICES = {
        StudentIntent.CHIT_CHAT: {"tool_choice": None, "max_rounds": 1},
        StudentIntent.OFF_TOPIC: {"tool_choice": None, "max_rounds": 1},
        StudentIntent.NEW_TOPIC: {"tool_choice": "any", "max_rounds": 1},
        StudentIntent.SKIP_TOPIC: {"tool_choice": None, "max_rounds": 1},
        StudentIntent.IN_TOPIC_RESPONSE: {"tool_choice": "auto", "max_rounds": 1},
        StudentIntent.REQUEST_PRACTICE: {"tool_choice": "any", "max_rounds": 1},
        StudentIntent.END_SESSION: {"tool_choice": "any", "max_rounds": 1},
    }

    _TEXT_MODEL_ID = "Qwen/Qwen3.6-35B-A3B-fp8"
    _VISION_MODEL_ID = "Qwen/Qwen3.5-397B-A17B-int4"

    _RCP_CLIENT = {"base_url": config.rcp.base_url, "api_key": config.rcp.api_key}
    _DETERMINISTIC_KWARGS = {
        "temperature": 0.0,
        "top_p": 1.0,
        "presence_penalty": 0.0,
        "extra_body": {
            "top_k": 20,
            "min_p": 0.0,
            "repetition_penalty": 1.0,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    }

    model = ChatOpenAI(
        **_RCP_CLIENT,
        model=_TEXT_MODEL_ID,
        timeout=30,
        stream_usage=True,
        temperature=0.8,
        top_p=0.9,
        max_tokens=1024,
        presence_penalty=1.0,
        frequency_penalty=0.0,
        extra_body={
            "top_k": 20,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )

    light_model = ChatOpenAI(
        **_RCP_CLIENT,
        model=_TEXT_MODEL_ID,
        timeout=30,
        stream_usage=False,
        **_DETERMINISTIC_KWARGS,
    )

    vision_model = ChatOpenAI(
        **_RCP_CLIENT,
        model=_VISION_MODEL_ID,
        timeout=60,
        stream_usage=False,
        **_DETERMINISTIC_KWARGS,
    )

    # --- Prompts ------------------------------------

    @cached_property
    def course_name(self) -> str:
        """The course this tutor teaches, from the course directory's own
        `course_name.md`. A context value rather than a template include,
        because the quiz page needs it in Python too."""
        return render_prompt(self.prompt_search_path, "course_name.md")

    def prompt_context(self) -> dict:
        return super().prompt_context() | {"course_name": self.course_name, "languages": LANGUAGES}

    # --- RAG ----------------------------------------

    def build_tools(self) -> list[BaseTool]:
        return [
            make_search_tool(
                index=self.index,
                args_schema=self.tool_input_schema,
                description=render_prompt(self.prompt_search_path, "tool_description.md", **self.prompt_context()),
            )
        ]

    # --- Graph --------------------------------------

    @staticmethod
    def _route_after_transcribe_image(state: ExpliqueBotState) -> Node | tuple[Node, ...]:
        """A turn whose content couldn't be transcribed (see
        `app/bots/nodes/transcribe_image.py`) is answered directly, without running
        classify/evaluate against a placeholder standing in for it — and without
        detecting the student's language, since there is no readable turn to read it from.

        A readable turn fans out: `detect_language` is a leaf whose write lands
        before the next superstep reads it, so nothing has to join it back.
        """
        if state.get("category") == MessageEvent.CONTENT_UNREADABLE:
            return Node.RESPOND
        return (Node.CLASSIFY, Node.DETECT_LANGUAGE)

    @staticmethod
    def _route_after_classify(state: ExpliqueBotState) -> Node:
        """Social and skip turns answer directly; substantive turns and the
        end-of-session recap retrieve first (the recap needs sources to cite)."""
        direct_categories = (
            StudentIntent.CHIT_CHAT,
            StudentIntent.OFF_TOPIC,
            StudentIntent.SKIP_TOPIC,
        )
        if state["category"] in direct_categories:
            return Node.RESPOND
        return Node.RETRIEVE

    @staticmethod
    def _route_after_retrieve(state: ExpliqueBotState) -> Node | tuple[Node, ...]:
        """Where a turn goes once its material is in hand:

        - end-session → summarize
        - new-topic → respond, straight to the intro
        - request-practice → practice (see `nodes/practice.py` for how
          `practice_response` then reaches `respond`)
        - everything else → evaluate and plan_challenge, fanned out in
          parallel so plan_challenge's latency hides behind evaluate's
          instead of adding to the critical path
        """
        category = state["category"]
        if category == StudentIntent.END_SESSION:
            return Node.SUMMARIZE
        if category == StudentIntent.NEW_TOPIC:
            return Node.RESPOND
        if category == StudentIntent.REQUEST_PRACTICE:
            return Node.PRACTICE
        return (Node.EVALUATE, Node.PLAN_CHALLENGE)

    @staticmethod
    async def _post_retrieve(_state: ExpliqueBotState) -> None:
        """Junction where the two retrieval paths (a tool call or none) converge,
        so a single conditional edge can dispatch by student intent. Does no work
        itself; `_route_after_retrieve` reads the state and dispatches."""
        return None

    def build_graph(self) -> CompiledStateGraph:
        """Compile the explique flow:

        transcribe_image ─┬─ (content unreadable) ────────────────────────────────────────► respond
                          ├─ detect_language (leaf; writes `lang_code`)
                          └─ classify ─┬─ (chit-chat / off-topic / skip-topic) ─► respond
                                       └─ retrieve ─┬─ (tool call) ────► tools ──────┐
                                                    └─ (no tool call) ───────────────┴─► post_retrieve ─┬─ (new-topic) ──────────────► respond
                                                                                                        ├─ (request-practice) ─► practice ─► respond
                                                                                                        ├─ (end-session) ─► summarize ─► respond
                                                                                                        └─ (in-topic-response) ─┬─ evaluate ────────┬─► select_action ─► respond
                                                                                                                                └─ plan_challenge ──┘

        Every one of those paths ends through the reply check:

            respond ─────────► evaluate_response ──(accepted, or budget spent)──► END
               ▲                       │
               └───────(rejected)──────┘

        `respond` writes to `candidate_response`, not `messages`, so a rejected candidate can be
        regenerated before the student sees it. `evaluate_response` is what creates the message.
        The one exception is a filled practice request: its reply was already computed
        upstream, so `respond` returns it straight to END.

        `tools` normally returns to `post_retrieve` as drawn above, but can loop back to
        `retrieve` instead for another round, up to the cap `INTENT_TOOL_CHOICES` declares
        per intent — so a later round can see the earlier one's result before deciding
        whether to search again.
        """
        tools = self.build_tools()

        workflow = StateGraph(ExpliqueBotState, context_schema=Bot)
        workflow.add_node(
            Node.TRANSCRIBE_IMAGE,
            make_image_transcriber_node(
                COMPILERS.get(ExpliqueTask.TRANSCRIBE_IMAGE),
                on_unreadable=MessageEvent.CONTENT_UNREADABLE,
            ),
        )
        workflow.add_node(
            Node.DETECT_LANGUAGE,
            make_detect_language_node(COMPILERS.get(ExpliqueTask.DETECT_LANGUAGE)),
        )
        workflow.add_node(
            Node.CLASSIFY,
            make_classify_node(
                self.INTENT_TOOL_CHOICES,
                fallback=StudentIntent.CHIT_CHAT,
                compiler=COMPILERS.get(ExpliqueTask.CLASSIFY),
            ),
        )
        workflow.add_node(
            Node.RETRIEVE,
            make_retrieve_node(tools, on_text=Node.POST_RETRIEVE, on_tools=Node.TOOLS, self_node=Node.RETRIEVE),
        )

        workflow.add_node(Node.TOOLS, make_tools_node(tools, back_to=None))
        workflow.add_node(Node.POST_RETRIEVE, self._post_retrieve)
        workflow.add_node(Node.EVALUATE, evaluate_node)
        workflow.add_node(Node.PLAN_CHALLENGE, plan_challenge_node)
        workflow.add_node(Node.PRACTICE, practice_node)
        workflow.add_node(Node.SELECT_ACTION, select_action_node)
        workflow.add_node(Node.SUMMARIZE, summarize_node)
        workflow.add_node(Node.RESPOND, make_respond_node(on_candidate_response=Node.EVALUATE_RESPONSE))
        workflow.add_node(Node.EVALUATE_RESPONSE, make_evaluate_response_node(on_retry=Node.RESPOND))

        workflow.set_entry_point(Node.TRANSCRIBE_IMAGE)
        workflow.add_conditional_edges(Node.TRANSCRIBE_IMAGE, self._route_after_transcribe_image)
        workflow.add_conditional_edges(Node.CLASSIFY, self._route_after_classify)
        workflow.add_conditional_edges(Node.POST_RETRIEVE, self._route_after_retrieve)
        workflow.add_edge(Node.EVALUATE, Node.SELECT_ACTION)
        workflow.add_edge(Node.PLAN_CHALLENGE, Node.SELECT_ACTION)
        workflow.add_edge(Node.SELECT_ACTION, Node.RESPOND)
        workflow.add_edge(Node.PRACTICE, Node.RESPOND)
        workflow.add_edge(Node.SUMMARIZE, Node.RESPOND)
        # No edge out of RESPOND or EVALUATE_RESPONSE: both route with `Command`,
        # since where they go depends on the candidate response rather than on the state alone.

        return workflow.compile()
