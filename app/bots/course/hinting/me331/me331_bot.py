from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.hinting.hinting_bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "lecture_notes", "recommended_reading"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["serie"]] = Field(
        default=None,
        description="Optional subtype for practice content (also known as studio).",
    )
    number: Optional[str] = Field(
        default=None,
        description="Studio number, e.g. 'Studio 1, Problem 3d' → '1'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Problem/exercise number within the studio, e.g. 'Studio 1, Problem 3d' → '3'.",
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["mock_exam"]] = Field(
        default=None,
        description="Optional subtype, e.g. 'Mock exam' → 'mock_exam'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exam, e.g. 'Mock exam 2026 Q15' → '15'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for ME-331 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """
    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class ME331Bot(HintingCourseBot):
    name = 'ME-331'
    index = 'course_me331'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'chatbot_me_331']
    tool_input_schema = ToolInput
