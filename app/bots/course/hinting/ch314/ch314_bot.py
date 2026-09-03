from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.hinting.hinting_bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["theory", "theory_slides"]] = Field(
        default=None,
        description="Optional subtype for theory content. 'theory' = general lecture notes / polycopié, 'theory_slides' = lecture slides.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["exercise",]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Number of the exercise set. Always an integer.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exercise set. Always an integer.",
    )


class ToolInput(BaseModel):
    """
    Search schema for CH-314 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class CH314Bot(HintingCourseBot):
    name = "CH-314"
    index = "course_ch314"
    groups = []
    tool_input_schema = ToolInput
