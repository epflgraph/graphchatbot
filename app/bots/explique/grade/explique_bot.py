from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.bots.base import Bot
from app.bots.explique.compilers.respond import ResponseCompiler
from app.bots.explique.explique_bot import ExpliqueBot
from app.bots.explique.grade.compilers.classify import GradeClassifyCompiler
from app.bots.explique.grade.compilers.detect_language import GradeLanguageDetectorCompiler
from app.bots.explique.grade.compilers.retrieve import GradeRetrieveCompiler
from app.bots.explique.grade.compilers.transcribe_image import GradeImageTranscriptionCompiler
from app.bots.explique.grade.completion import topic_covered
from app.bots.explique.grade.models import GradeStudentIntent
from app.bots.explique.grade.node_names import GradeNode
from app.bots.explique.grade.nodes.derive_topic_points import derive_topic_points_node
from app.bots.explique.grade.nodes.evaluate import evaluate_node
from app.bots.explique.grade.nodes.finish import finish_node
from app.bots.explique.grade.nodes.invite import invite_node
from app.bots.explique.grade.nodes.lock_topic import lock_topic_node
from app.bots.explique.grade.nodes.no_answer import no_answer_node
from app.bots.explique.grade.nodes.plan_challenge import plan_challenge_node
from app.bots.explique.grade.nodes.present_menu import present_menu_node
from app.bots.explique.grade.nodes.redirect import redirect_node
from app.bots.explique.grade.nodes.respond import make_respond_node
from app.bots.explique.grade.nodes.transcribe_image import make_transcribe_image_node
from app.bots.explique.grade.state import GradeBotState
from app.bots.explique.grade.topics import Topics
from app.bots.explique.grade.transcript import graded_turns
from app.bots.explique.grade.tutor_action import select_tutor_action
from app.bots.explique.models import MessageEvent, StudentIntent
from app.bots.explique.node_names import Node
from app.bots.explique.nodes.evaluate_response import make_evaluate_response_node
from app.bots.explique.nodes.select_action import make_select_action_node
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.detect_language import make_detect_language_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.bots.nodes.transcribe_image import make_image_transcriber_node


class ExpliqueGradeBot(ExpliqueBot):
    """
    Abstract base for 'grade' bots: the exam-like flavor of explique.

    A session is graded on one curriculum topic the student picks before anything else
    happens; nothing else earns a reply, and covering that topic is what ends it. Up to
    the pick, no model runs but the language detector: the menu is the poller's list,
    the pick is string comparison, and the reply is a template.

    Subclasses must define: name, index, course_id, groups.
    """

    # Course index (RAG).
    index: str

    # The Moodle course this bot's gates live in. Not optional: the menu comes from that
    # course's quizzes, so a bot without one has no exercise to run.
    course_id: int

    # The topics this course's quizzes are tagged with, republished by every polling pass.
    topics: Topics = Topics()

    # Every node that speaks to the student writes its own text to the stream,
    # canned messages included, so the student sees one pacing throughout.
    # Listing any of them here would send that node's message a second time.
    model_nodes = ()

    # The tutor's intents plus the one an exam needs: a malicious turn that instructs the
    # bot instead of explaining, kept off the graded path so it is never scored.
    INTENT_TOOL_CHOICES = ExpliqueBot.INTENT_TOOL_CHOICES | {GradeStudentIntent.JAILBREAK: {"tool_choice": None}}

    # --- Graph --------------------------------------

    @staticmethod
    def _direct_reply(state: GradeBotState) -> GradeNode | None:
        """The node that answers this turn from a template, or None for the graded exchange."""
        # A session that is over stays over, even once its topic has left the menu and no
        # lock resolves: nothing is classified, retrieved or evaluated, and the Moodle
        # write cannot fire twice.
        if state["session_finished"]:
            return GradeNode.FINISH
        topic_lock = state["topic_lock"]
        if topic_lock is None:
            return GradeNode.PRESENT_MENU
        if topic_lock.is_in_latest_turn(state["messages"]):
            return GradeNode.INVITE
        return None

    @classmethod
    def _route_after_derive_topic_points(cls, state: GradeBotState) -> Node:
        """A direct reply renders a template in the student's language, so it detects that first."""
        return Node.DETECT_LANGUAGE if cls._direct_reply(state) else Node.TRANSCRIBE_IMAGE

    @classmethod
    def _route_after_detect_language(cls, state: GradeBotState) -> GradeNode | str:
        return cls._direct_reply(state) or END

    @staticmethod
    def _route_after_classify(state: GradeBotState) -> Node | GradeNode:
        """A graded session answers nothing but the topic it locked.
        Every other intent is redirected without retrieving."""
        if state["category"] == StudentIntent.IN_TOPIC_RESPONSE:
            return Node.RETRIEVE
        return GradeNode.REDIRECT

    def _route_after_select_action(self, state: GradeBotState) -> Node | GradeNode:
        """A covered topic ends the exercise instead of extending it; a turn that could not be evaluated gets
        NO_ANSWER."""
        if state["student_state"] is None:
            return GradeNode.NO_ANSWER
        topic_lock = state["topic_lock"]
        # A jailbreak turn explained nothing, so it does not count towards the floor.
        graded = graded_turns(self.prompt_search_path, topic_lock.topic, state["messages"])
        is_topic_covered = topic_covered(
            plan=state.get("challenge_plan"),
            student_state=state["student_state"],
            explaining_turns=topic_lock.explaining_turns(graded),
        )
        return GradeNode.FINISH if is_topic_covered else Node.RESPOND

    def build_graph(self) -> CompiledStateGraph:
        """Compile the graded flow:

        lock_topic ─► derive_topic_points ─┬─ (a direct reply) ─► detect_language ─┬─ (no topic yet) ────────► present_menu ─► END
                                           │                                      ├─ (picked in this turn) ─► invite ───────► END
                                           │                                      └─ (already finished) ────► finish ───────► END
                                           └─ (picked earlier) ─► transcribe_image ─► … ─► evaluate_response ─► END

        `lock_topic` is the entry point, so nothing is fetched or transcribed before a topic is
        picked. `derive_topic_points` runs before the branches so every turn past the lock reads a
        warm cache; the standard is keyed on the topic's material and shared across students.

        From `transcribe_image` on, the graded exchange is the tutor's without its exits:

        transcribe_image ─┬─ (content unreadable) ────────────────────────────────────────────────────► respond
                          ├─ detect_language (writes `lang_code`, then ends)
                          └─ classify ─┬─ (anything but an explanation) ─────────────────────────────► redirect ─► END
                                       └─ retrieve ─┬─ (tool call) ────► tools ──────┐
                                                    └─ (no tool call) ───────────────┴─► post_retrieve ─┬─ evaluate ───────┬─► select_action ─┬─ (covered) ─► finish ─► END
                                                                                                        └─ plan_challenge ─┘                  ├─ (not evaluated) ─► no_answer ─► END
                                                                                                                                              └─ (points left) ─► respond

            respond ─────────► evaluate_response ──(accepted, or budget spent)──► END
               ▲                       │
               └───────(rejected)──────┘

        `respond` streams through a `StreamGate` and writes `candidate_response`, not `messages`;
        `evaluate_response` creates the message and streams what the gate held back. `finish` is
        the only way out: it runs the recap alongside the Moodle write, and covering the topic is
        what earns it. `no_answer` sends the canned apology when `evaluate` failed, since there
        is no verdict to answer from.
        """
        tools = self.build_tools()

        workflow = StateGraph(GradeBotState, context_schema=Bot)
        workflow.add_node(GradeNode.LOCK_TOPIC, lock_topic_node)
        workflow.add_node(GradeNode.DERIVE_TOPIC_POINTS, derive_topic_points_node)
        workflow.add_node(GradeNode.PRESENT_MENU, present_menu_node)
        workflow.add_node(GradeNode.INVITE, invite_node)
        workflow.add_node(GradeNode.REDIRECT, redirect_node)
        workflow.add_node(GradeNode.FINISH, finish_node)
        workflow.add_node(
            Node.TRANSCRIBE_IMAGE,
            make_transcribe_image_node(
                make_image_transcriber_node(
                    GradeImageTranscriptionCompiler,
                    on_unreadable=MessageEvent.CONTENT_UNREADABLE,
                )
            ),
        )
        workflow.add_node(
            Node.DETECT_LANGUAGE,
            make_detect_language_node(GradeLanguageDetectorCompiler),
        )
        # The tutor's nodes are typed on the state the tutor writes, and a node receives
        # only the keys its type names; these read the graded conversation, which
        # takes the lock, so the graded state is declared for them.
        workflow.add_node(
            Node.CLASSIFY,
            make_classify_node(
                self.INTENT_TOOL_CHOICES,
                fallback=StudentIntent.IN_TOPIC_RESPONSE,
                compiler=GradeClassifyCompiler,
                max_retries=1,
            ),
            input_schema=GradeBotState,
        )
        workflow.add_node(
            Node.RETRIEVE,
            make_model_node(
                tools,
                compiler=GradeRetrieveCompiler,
                on_text=Node.POST_RETRIEVE,
                on_tools=Node.TOOLS,
                max_tool_rounds=self.MAX_RETRIEVAL_ROUNDS,
                text_is_reply=False,
            ),
            input_schema=GradeBotState,
        )

        workflow.add_node(Node.TOOLS, make_tools_node(tools))
        workflow.add_node(Node.POST_RETRIEVE, self._post_retrieve)
        workflow.add_node(Node.EVALUATE, evaluate_node)
        workflow.add_node(GradeNode.NO_ANSWER, no_answer_node)
        workflow.add_node(Node.PLAN_CHALLENGE, plan_challenge_node)
        workflow.add_node(Node.SELECT_ACTION, make_select_action_node(select_tutor_action))
        workflow.add_node(Node.RESPOND, make_respond_node(on_candidate_response=Node.EVALUATE_RESPONSE))
        workflow.add_node(
            Node.EVALUATE_RESPONSE, make_evaluate_response_node(on_retry=Node.RESPOND, compiler=ResponseCompiler)
        )

        workflow.set_entry_point(GradeNode.LOCK_TOPIC)
        workflow.add_edge(GradeNode.LOCK_TOPIC, GradeNode.DERIVE_TOPIC_POINTS)
        workflow.add_conditional_edges(GradeNode.DERIVE_TOPIC_POINTS, self._route_after_derive_topic_points)
        workflow.add_edge(GradeNode.PRESENT_MENU, END)
        workflow.add_edge(GradeNode.INVITE, END)
        workflow.add_edge(GradeNode.REDIRECT, END)
        workflow.add_edge(GradeNode.FINISH, END)
        workflow.add_edge(GradeNode.NO_ANSWER, END)
        workflow.add_conditional_edges(Node.DETECT_LANGUAGE, self._route_after_detect_language)
        workflow.add_conditional_edges(Node.TRANSCRIBE_IMAGE, self._route_after_transcribe_image)
        workflow.add_conditional_edges(Node.CLASSIFY, self._route_after_classify)
        workflow.add_edge(Node.POST_RETRIEVE, Node.EVALUATE)
        workflow.add_edge(Node.POST_RETRIEVE, Node.PLAN_CHALLENGE)
        workflow.add_edge(Node.EVALUATE, Node.SELECT_ACTION)
        workflow.add_edge(Node.PLAN_CHALLENGE, Node.SELECT_ACTION)
        workflow.add_conditional_edges(Node.SELECT_ACTION, self._route_after_select_action)

        return workflow.compile()
