import logging
from enum import StrEnum
from functools import cached_property

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.bots.base import Bot, BotState
from app.bots.compilers.classify import ClassifyCompiler
from app.bots.compilers.respond import ResponseCompiler
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.compilation.templates import render_prompt
from app.interfaces.graphai import RAGResult, graphai

logger = logging.getLogger(__name__)


class RequestType(StrEnum):
    """What the student is asking for. `classify` picks one per turn, and each
    one decides whether the course material is searched."""

    GREETING = "greeting"
    THEORY = "theory"
    PRACTICE = "practice"
    ADMIN = "admin"
    UNRELATED = "unrelated"


CATEGORIES = {
    RequestType.GREETING: {
        "description": "The user is just greeting the assistant or similar.",
        "tool_choice": None,
    },
    RequestType.THEORY: {
        "description": "The user's request is about a theoretical aspect of the course.",
        "tool_choice": "any",
    },
    RequestType.PRACTICE: {
        "description": "The user's request is about an exercise, lab session, practice exam or similar.",
        "tool_choice": "any",
    },
    RequestType.ADMIN: {
        "description": "The user's request is about an administrative aspect of the course, like schedule, rooms, grading, or logistics.",
        "tool_choice": None,
    },
    RequestType.UNRELATED: {
        "description": "The user's request is completely unrelated to the course.",
        "tool_choice": None,
    },
}


class CourseBot(Bot):
    """
    Abstract base for course tutor bots.

    Subclasses must define:
        name: str
        index: str
        groups: list[str]
        tool_input_schema: type[BaseModel]  — ToolInput with course-specific filters

    Subclasses may override:
        CATEGORIES
        build_tools()
        build_graph()
    """

    tool_input_schema: type[BaseModel]

    CATEGORIES: dict = CATEGORIES

    # --- Prompts ---

    @cached_property
    def course_name(self) -> str:
        """The course this bot tutors, from the course directory's own
        `course-name.md`. A context value rather than a template include,
        because the prompts name the course mid-sentence."""
        return render_prompt(self.prompt_search_path, "course-name.md")

    def prompt_context(self) -> dict:
        return super().prompt_context() | {"course_name": self.course_name, "categories": self.CATEGORIES}

    # --- Tools ---

    @staticmethod
    def _format_results(result: RAGResult) -> list[dict]:
        formatted = []
        for chunk in result.chunks:
            item = {
                "type": chunk.chunk_type,
                "title": chunk.title,
                "week": chunk.week,
                "number": chunk.number,
                "url": chunk.original_link,
                "page": chunk.page,
                "position": chunk.position,
                "content.fr": chunk.content_fr,
                "content.en": chunk.content_en,
            }

            video_lectures = chunk.associated_video_lectures or []
            if video_lectures:
                item["associated_video_lectures"] = [
                    {"title": video_lecture.title, "url": video_lecture.original_link}
                    for video_lecture in video_lectures
                ]

            formatted.append({key: value for key, value in item.items() if value is not None})
        return formatted

    async def search_course_material(self, query: str, filters: BaseModel | None = None) -> list:
        logger.info(f"filters=`{filters}`")

        result = await graphai.rag_retrieve(index=self.index, texts=[query], filters=filters)

        logger.info(f"Retrieved {len(result.chunks)} chunks.")

        return self._format_results(result)

    def build_tools(self) -> list:
        description = render_prompt(self.prompt_search_path, "tool-description.md", **self.prompt_context())
        return [
            tool("search_course_material", args_schema=self.tool_input_schema, description=description)(
                self.search_course_material
            )
        ]

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)
        workflow.add_node(
            "classify", make_classify_node(self.CATEGORIES, fallback=RequestType.GREETING, compiler=ClassifyCompiler)
        )
        workflow.add_node("model", make_model_node(tools, compiler=ResponseCompiler))
        workflow.add_node("tools", make_tools_node(tools))
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "model")

        return workflow.compile()
