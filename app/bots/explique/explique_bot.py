from functools import cached_property

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from app.bots.base import Bot
from app.bots.explique.models import MessageEvent, StudentIntent
from app.bots.explique.node_names import Node
from app.bots.explique.retrieval import ToolInput, make_search_tool
from app.bots.explique.state import ExpliqueBotState
from app.bots.languages import LANGUAGES
from app.compilation.templates import render_prompt
from app.config import config


class ExpliqueBot(Bot):
    """Abstract base for both explique flavours: the clients, the prompt context, the search
    tool, and the routers the two graphs share. Each flavour builds its own graph."""

    # The course material to search, or None for a course with none. Declared
    # without a default, so omitting it is still an error rather than an opt-out.
    index: str | None

    # The search tool's argument schema; override to narrow or extend `ToolInput`'s filters.
    tool_input_schema = ToolInput

    # A ceiling, not a quota: one round may do several searches, and a turn
    # needing no course material searches none.
    MAX_RETRIEVAL_ROUNDS = 1

    # How `retrieve` binds its search tool per intent. `classify` writes the
    # choice into state; `retrieve` spends it on its first round only.
    INTENT_TOOL_CHOICES = {
        StudentIntent.CHIT_CHAT: {"tool_choice": None},
        StudentIntent.OFF_TOPIC: {"tool_choice": None},
        StudentIntent.NEW_TOPIC: {"tool_choice": None},
        StudentIntent.SKIP_TOPIC: {"tool_choice": None},
        StudentIntent.IN_TOPIC_RESPONSE: {"tool_choice": "auto"},
        StudentIntent.REQUEST_PRACTICE: {"tool_choice": "any"},
        StudentIntent.END_SESSION: {"tool_choice": "any"},
    }

    _TEXT_MODEL_ID = "Qwen/Qwen3.6-35B-A3B-fp8"
    _VISION_MODEL_ID = "Qwen/Qwen3.5-397B-A17B-int4"

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
        base_url=config.rcp.base_url,
        api_key=config.rcp.api_key,
        model=_TEXT_MODEL_ID,
        timeout=30,
        max_retries=1,
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
        base_url=config.rcp.base_url,
        api_key=config.rcp.api_key,
        model=_TEXT_MODEL_ID,
        timeout=30,
        max_retries=1,
        stream_usage=False,
        **_DETERMINISTIC_KWARGS,
    )

    vision_model = ChatOpenAI(
        base_url=config.rcp.base_url,
        api_key=config.rcp.api_key,
        model=_VISION_MODEL_ID,
        timeout=60,
        max_retries=1,
        stream_usage=False,
        **_DETERMINISTIC_KWARGS,
    )

    # --- Prompts ------------------------------------

    @cached_property
    def course_name(self) -> str:
        """The course this bot teaches, from the course directory's own
        `course-name.md`. A context value rather than a template include,
        because the quiz page needs it in Python too."""
        return render_prompt(self.prompt_search_path, "course-name.md")

    def prompt_context(self) -> dict:
        return super().prompt_context() | {"course_name": self.course_name, "languages": LANGUAGES}

    # --- RAG ----------------------------------------

    def build_tools(self) -> list[BaseTool]:
        """The search tool, or none at all for a course with no index."""
        if self.index is None:
            return []

        return [
            make_search_tool(
                index=self.index,
                args_schema=self.tool_input_schema,
                description=render_prompt(self.prompt_search_path, "tool-description.md", **self.prompt_context()),
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
    async def _post_retrieve(_state: ExpliqueBotState) -> None:
        """Junction where the two retrieval paths (a tool call or none) converge, so what
        follows has one source. Does no work itself."""
        return None
