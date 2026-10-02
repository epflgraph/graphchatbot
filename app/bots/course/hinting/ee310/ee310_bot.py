from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.hinting.hinting_bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["theory_slides"]] = Field(
        default=None,
        description="Optional subtype for theory content. 'theory_slides' = lecture slides.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["pw", "practical_work"]] = Field(
        default=None,
        description="Optional subtype for practice content. The course splits its practical works across both values, so omit it to search them all.",
    )
    number: Optional[int] = Field(
        default=None,
        description="Practical work (PW / TP) number, ignoring any part letter, e.g. 'PW3A' → 3, 'TP 5C' → 5.",
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    number: Optional[str] = Field(
        default=None,
        description="Year of the exam, e.g. 'Midterm 2024' → '2024'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exam, e.g. 'Midterm 2019 exo 11' → '11'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for EE-310 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class EE310Bot(HintingCourseBot):
    name = "EE-310"
    index = "course_ee310"
    groups = []
    tool_input_schema = ToolInput
    content_language = "en"
