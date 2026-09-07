from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.direct.direct_bot import DirectCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["theory", "theory_slides"]] = Field(
        default=None,
        description="Optional subtype for theory content. 'theory' = general lecture notes / polycopié, 'theory_slides' = lecture slides.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["quiz"]] = Field(
        default=None,
        description="Optional subtype for practice content. 'quiz' = quiz/exercise sheets.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Quiz number. Exercises are numbered with three integers (e.g. 3.1.4), but search using the first two: number=3, sub_number=1.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise group within the quiz. For exercise 3.1.4, use sub_number=1.",
    )


class ToolInput(BaseModel):
    """
    Search schema for BIO-695 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class BIO695Bot(DirectCourseBot):
    name = "BIO-695"
    index = "course_bio695"
    groups = []
    tool_input_schema = ToolInput
