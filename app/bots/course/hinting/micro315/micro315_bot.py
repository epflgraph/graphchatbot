from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.hinting.hinting_bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "recommended_reading"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["lab", "lab_lib", "lab_wiki"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Lab number, e.g. 'Lab 3' -> '3', 'lab intro' -> '0'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MICRO-315 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """
    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class MICRO315Bot(HintingCourseBot):
    name = 'MICRO-315'
    index = 'course_micro315'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'chatbot_micro_315']
    tool_input_schema = ToolInput

    CATEGORIES = {
        'greeting': {'description': "The user is just greeting the assistant or similar.", 'tool_choice': None},
        'theory': {'description': "The user is asking a question about a certain concept, a course lecture or the course slides.", 'tool_choice': 'any'},
        'exercise': {'description': "The user is asking a question about a lab session or a course exercise or assignment, but not related to code.", 'tool_choice': 'any'},
        'exercise-coding': {'description': "The user is asking a question about a lab session or a course exercise or assignment, and the question is related to code or coding environments, or the user is pasting some piece of the assignment.", 'tool_choice': 'any'},
        'debugging': {'description': "The user is asking help to debug code that has bugs at the execution level and not compilation. Typically, the user asks about resolving kernel panic states (robot in panic handler), in which the robot blinks four red LEDs.", 'tool_choice': 'any'},
        'admin': {'description': "The user's request is about an administrative aspect of the course, like schedule, rooms, grading, logistics or similar.", 'tool_choice': None},
        'unrelated': {'description': "The user's request is completely unrelated to the course.", 'tool_choice': None},
    }
