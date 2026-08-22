import logging

from langchain.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.interfaces.graphai import RAGResult, graphai

logger = logging.getLogger(__name__)


class Filters(BaseModel):
    """Generic type/subtype narrowing shared by every explique domain."""

    # FUTURE: a `week` cutoff ("nothing not yet taught") can't be a field here
    # — it must come from a trusted source, not the LLM, and be applied as a
    # post-filter on RAGChunk.week (the index only does exact-match).
    type: str | None = Field(default=None, description="Content type, e.g. 'theory' or 'practice'.")
    subtype: str | None = Field(
        default=None,
        description="Content subtype, e.g. 'lecture_slides', 'video_lecture', 'exercises', 'quiz'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for retrieving reference material for an explique domain.
    """

    query: str = Field(description="The student's query, e.g. 'merge sort' or 'quicksort worst case'.")
    filters: Filters = Field(
        default_factory=Filters,
        description="Optional type/subtype filters to narrow retrieval within the RAG index.",
    )


def _format_results(result: RAGResult) -> list[dict]:
    """Keep only concept-relevant fields; explique material has no course metadata."""
    formatted = []
    for chunk in result.chunks:
        chunk_dict = {
            "type": chunk.chunk_type,
            "title": chunk.title,
            "url": chunk.original_link,
            "page": chunk.page,
            "position": chunk.position,
            "content": chunk.content or chunk.content_en or chunk.content_fr,
        }
        formatted.append({key: value for key, value in chunk_dict.items() if value is not None})
    return formatted


def make_search_tool(index: str, args_schema: type[BaseModel], description: str) -> BaseTool:
    """Returns the course-material search tool bound to one bot's RAG index."""

    async def search_course_material(query: str, filters: BaseModel | None = None) -> list:
        """Retrieve reference material for the student's query."""
        logger.info(f"Retrieving explique material: query={query!r}, filters={filters!r}")
        result = await graphai.rag_retrieve(
            index=index,
            texts=[query],
            filters=filters,
        )
        logger.info(f"Retrieved {len(result.chunks)} chunks for query={query!r}")

        return _format_results(result)

    return tool("search_course_material", args_schema=args_schema, description=description)(search_course_material)
