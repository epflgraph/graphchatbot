from app.bots.artifacts.rich_response import CollapsibleBlock, RichResponse, TextBlock, VideoBlock
from app.bots.course.course_bot import RichResponseCourseBot


class DirectResponse(RichResponse):
    """A direct reply: text, sections to expand, and lecture videos."""

    blocks: tuple[TextBlock | CollapsibleBlock | VideoBlock, ...]


class DirectCourseBot(RichResponseCourseBot):
    """Course bot that gives direct, complete answers."""

    response_schema = DirectResponse
