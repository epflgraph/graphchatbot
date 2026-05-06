from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.hinting.bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "textbook"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["serie"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Serie number, e.g. 'Série 4' → '4'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MATH-240 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """
    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class MATH240Bot(HintingCourseBot):
    name = 'MATH-240'
    index = 'course_math240'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'chatbot_math_240']
    tool_input_schema = ToolInput
