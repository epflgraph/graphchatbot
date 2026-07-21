from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.direct.direct_bot import DirectCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "book"]] = Field(
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
        description="""Serie (N), e.g. 'Serie 1 Fundamentals. Ex 5 a) What is...' -> 'number': '1', 'Series 3.2 CentralTendency. Ex 2' -> 'number': '3', , 'S04 Ex12' -> 'number': '4'""",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="It's Serie number followed by '.' followed by the exercise number within the serie (N), e.g. 'Série 3 ex 3.6' -> 'sub_number': '3.6', 'Series 1 Problem 1.6' -> 'sub_number': '1.6', 'Serie 1 exercise 17' -> 'sub_number': '1.17',  'exercise 1.6' -> 'sub_number': '1.6', 'Serie 8.41' -> 'sub_number': '8.41' ",
    )


class ToolInput(BaseModel):
    """
    Search schema for Statistics course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class StatisticsBot(DirectCourseBot):
    name = "statistics"
    index = "course_swissunidemo"
    groups = []
    tool_input_schema = ToolInput
