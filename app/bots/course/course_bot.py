import inspect
import logging
from pathlib import Path

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.bots.base import BOTS_ROOT, Bot, BotState
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.bots.prompts import resolve
from app.interfaces.graphai import graphai

logger = logging.getLogger(__name__)


CATEGORIES = {
    "greeting": {
        "description": "The user is just greeting the assistant or similar.",
        "tool_choice": None,
    },
    "theory": {
        "description": "The user's request is about a theoretical aspect of the course.",
        "tool_choice": "any",
    },
    "practice": {
        "description": "The user's request is about an exercise, lab session, practice exam or similar.",
        "tool_choice": "any",
    },
    "admin": {
        "description": "The user's request is about an administrative aspect of the course, like schedule, rooms, grading, or logistics.",
        "tool_choice": None,
    },
    "unrelated": {
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

    # --- Tools ---

    @staticmethod
    def _format_results(results: list) -> list:
        formatted = []
        for r in results:
            item = {
                "type": f"{r.get('type')}: {r.get('subtype')}",
                "title": r.get("title"),
                "week": r.get("week"),
                "number": r.get("number"),
                "url": r.get("original_link"),
                "page": r.get("page"),
                "position": r.get("position"),
                "content.fr": r.get("content.fr"),
                "content.en": r.get("content.en"),
            }

            video_lectures = r.get("associated_video_lectures") or []
            if video_lectures:
                item["associated_video_lectures"] = [
                    {"title": v.get("title"), "url": v.get("original_link")} for v in video_lectures
                ]

            formatted.append({k: v for k, v in item.items() if v is not None})
        return formatted

    async def search_course_material(self, query: str, filters) -> list:
        if isinstance(filters, BaseModel):
            filters_dict = filters.model_dump(exclude_none=True)
        elif isinstance(filters, dict):
            filters_dict = {k: v for k, v in filters.items() if v is not None}
        else:
            filters_dict = {}

        logger.info(f"filters=`{filters_dict}`")

        results = await graphai.rag_retrieve(index=self.index, texts=[query], filters=filters_dict)

        logger.info(f"Retrieved {len(results)} chunks.")

        return self._format_results(results)

    def build_tools(self) -> list:
        subclass_dir = Path(inspect.getfile(type(self))).parent
        description = resolve("tool_description", subclass_dir, BOTS_ROOT)
        return [
            tool("search_course_material", args_schema=self.tool_input_schema, description=description)(
                self.search_course_material
            )
        ]

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(BotState, context_schema=Bot)
        workflow.add_node("classify", make_classify_node(self.CATEGORIES))
        workflow.add_node("model", make_model_node(tools))
        workflow.add_node("tools", make_tools_node(tools, back_to="model"))
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "model")

        return workflow.compile()
