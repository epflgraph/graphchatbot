from app.bots.artifacts.rich_response import HintBlock, RichResponse, TextBlock, VideoBlock
from app.bots.course.course_bot import RichResponseCourseBot


class HintingResponse(RichResponse):
    """A hinting reply: text, hints to expand, and lecture videos."""

    blocks: tuple[TextBlock | HintBlock | VideoBlock, ...]


class HintingCourseBot(RichResponseCourseBot):
    """Course bot that gives Socratic, hint-based guidance."""

    response_schema = HintingResponse

    @staticmethod
    def may_cite(chunk: dict) -> bool:
        """Any document but practice material, which may hold the solutions."""
        return not chunk.get("type", "").startswith("practice")
