from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.hinting.hinting_bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "book"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["serie", "homework"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Serie or homework number, e.g. 'Série 2' → '2', 'Homework 13' → '13'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the serie. When subtype is 'homework', never filter by sub_number.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MATH-535 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """
    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class MATH535Bot(HintingCourseBot):
    name = 'MATH-535'
    index = 'course_math535'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'chatbot_math_535']
    tool_input_schema = ToolInput
