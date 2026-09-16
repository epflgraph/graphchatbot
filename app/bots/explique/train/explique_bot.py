from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot
from app.bots.explique.compilers.classify import ClassifyCompiler
from app.bots.explique.compilers.detect_language import LanguageDetectorCompiler
from app.bots.explique.compilers.evaluate import EvaluateCompiler
from app.bots.explique.compilers.respond import ResponseCompiler
from app.bots.explique.compilers.retrieve import RetrieveCompiler
from app.bots.explique.compilers.transcribe_image import ImageTranscriptionCompiler
from app.bots.explique.explique_bot import ExpliqueBot
from app.bots.explique.models import MessageEvent, StudentIntent
from app.bots.explique.node_names import Node
from app.bots.explique.nodes.evaluate import make_evaluate_node
from app.bots.explique.nodes.evaluate_response import make_evaluate_response_node
from app.bots.explique.nodes.select_action import make_select_action_node
from app.bots.explique.nodes.summarize import summarize_node
from app.bots.explique.train.node_names import TrainNode
from app.bots.explique.train.nodes.plan_challenge import plan_challenge_node
from app.bots.explique.train.nodes.practice import practice_node
from app.bots.explique.train.nodes.respond import make_respond_node
from app.bots.explique.train.state import TrainBotState
from app.bots.explique.train.tutor_action import select_tutor_action
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.detect_language import make_detect_language_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.bots.nodes.transcribe_image import make_image_transcriber_node


class ExpliqueTrainBot(ExpliqueBot):
    """
    Abstract base for 'explique' tutor bots.

    Pedagogy: the tutor asks the student to explain concepts in a domain, evaluates each
    explanation against reference material using a structured mental model, and responds
    accordingly (probe, hint, explain, motivate, challenge); the session is recapped
    with citations when the student ends it.

    Subclasses must define:
        - name: str
        - index: str | None
        - groups: list[str]
    """

    # The two nodes that reach the student: `respond` for a rendered quiz,
    # `evaluate_response` for a checked reply. Neither streams.
    model_nodes = (Node.RESPOND, Node.EVALUATE_RESPONSE)

    # --- Graph --------------------------------------

    @staticmethod
    def _route_after_classify(state: TrainBotState) -> Node:
        """A turn retrieves only if something downstream reads it."""
        direct_categories = (
            StudentIntent.CHIT_CHAT,
            StudentIntent.OFF_TOPIC,
            StudentIntent.SKIP_TOPIC,
            StudentIntent.NEW_TOPIC,
        )
        if state["category"] in direct_categories:
            return Node.RESPOND
        return Node.RETRIEVE

    @staticmethod
    def _route_after_retrieve(state: TrainBotState) -> Node | TrainNode | tuple[Node, ...]:
        """Where a turn goes once its material is in hand:

        - end-session → summarize
        - request-practice → practice (see `nodes/practice.py` for how
          `practice_response` then reaches `respond`)
        - everything else → evaluate and plan_challenge, fanned out in
          parallel so plan_challenge's latency hides behind evaluate's
          instead of adding to the critical path
        """
        category = state["category"]
        if category == StudentIntent.END_SESSION:
            return TrainNode.SUMMARIZE
        if category == StudentIntent.REQUEST_PRACTICE:
            return TrainNode.PRACTICE
        return (Node.EVALUATE, Node.PLAN_CHALLENGE)

    def build_graph(self) -> CompiledStateGraph:
        """Compile the explique flow:

        transcribe_image ─┬─ (content unreadable) ────────────────────────────────────────► respond
                          ├─ detect_language (leaf; writes `lang_code`)
                          └─ classify ─┬─ (chit-chat / off-topic / skip-topic / new-topic) ─► respond
                                       └─ retrieve ─┬─ (tool call) ────► tools ──────┐
                                                    └─ (no tool call) ───────────────┴─► post_retrieve ─┬─ (request-practice) ─► practice ─► respond
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

        `tools` goes wherever `retrieve` sent it, recorded in `active_node`: back to
        `retrieve` while rounds remain, so a later round can see the earlier one's
        result before deciding whether to search again, and on to `post_retrieve`
        once they don't. `tools` only obeys; the choice is `retrieve`'s.
        """
        tools = self.build_tools()

        workflow = StateGraph(TrainBotState, context_schema=Bot)
        workflow.add_node(
            Node.TRANSCRIBE_IMAGE,
            make_image_transcriber_node(
                ImageTranscriptionCompiler,
                on_unreadable=MessageEvent.CONTENT_UNREADABLE,
            ),
        )
        workflow.add_node(
            Node.DETECT_LANGUAGE,
            make_detect_language_node(LanguageDetectorCompiler),
        )
        workflow.add_node(
            Node.CLASSIFY,
            make_classify_node(
                self.INTENT_TOOL_CHOICES,
                fallback=StudentIntent.CHIT_CHAT,
                compiler=ClassifyCompiler,
            ),
        )
        workflow.add_node(
            Node.RETRIEVE,
            make_model_node(
                tools,
                compiler=RetrieveCompiler,
                on_text=Node.POST_RETRIEVE,
                on_tools=Node.TOOLS,
                max_tool_rounds=self.MAX_RETRIEVAL_ROUNDS,
                text_is_reply=False,
            ),
        )

        workflow.add_node(Node.TOOLS, make_tools_node(tools))
        workflow.add_node(Node.POST_RETRIEVE, self._post_retrieve)
        workflow.add_node(Node.EVALUATE, make_evaluate_node(EvaluateCompiler))
        workflow.add_node(Node.PLAN_CHALLENGE, plan_challenge_node)
        workflow.add_node(TrainNode.PRACTICE, practice_node)
        workflow.add_node(Node.SELECT_ACTION, make_select_action_node(select_tutor_action))
        workflow.add_node(TrainNode.SUMMARIZE, summarize_node)
        workflow.add_node(Node.RESPOND, make_respond_node(on_candidate_response=Node.EVALUATE_RESPONSE))
        workflow.add_node(
            Node.EVALUATE_RESPONSE, make_evaluate_response_node(on_retry=Node.RESPOND, compiler=ResponseCompiler)
        )

        workflow.set_entry_point(Node.TRANSCRIBE_IMAGE)
        workflow.add_conditional_edges(Node.TRANSCRIBE_IMAGE, self._route_after_transcribe_image)
        workflow.add_conditional_edges(Node.CLASSIFY, self._route_after_classify)
        workflow.add_conditional_edges(Node.POST_RETRIEVE, self._route_after_retrieve)
        workflow.add_edge(Node.EVALUATE, Node.SELECT_ACTION)
        workflow.add_edge(Node.PLAN_CHALLENGE, Node.SELECT_ACTION)
        workflow.add_edge(Node.SELECT_ACTION, Node.RESPOND)
        workflow.add_edge(TrainNode.PRACTICE, Node.RESPOND)
        workflow.add_edge(TrainNode.SUMMARIZE, Node.RESPOND)
        # No edge out of RESPOND or EVALUATE_RESPONSE: both route with `Command`,
        # since where they go depends on the candidate response rather than on the state alone.

        return workflow.compile()
