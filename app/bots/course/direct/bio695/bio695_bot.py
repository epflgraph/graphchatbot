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
    subtype: Optional[Literal["serie"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Serie/week number. Always an integer.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the serie/week. Always an integer.",
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
