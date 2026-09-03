from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.direct.direct_bot import DirectCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["theory", "theory_slides", "mediaspace_video"]] = Field(
        default=None,
        description="Optional subtype for theory content. 'theory' = general lecture notes / polycopié, 'theory_slides' = lecture slides, 'mediaspace_video' = course videos.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[
        Literal[
            "serie",
            "homework",
            "serie_entrainement",
            "serie_supplementaire",
        ]
    ] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Serie or homework number. Always an integer.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the serie or homework. Always an integer.",
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["exam", "midterm_exam"]] = Field(
        default=None,
        description="Optional subtype for exam content. 'exam' = final/general exams from past years, 'midterm_exam' = midterm exams from past years.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Year of the exam, e.g. 'Exam 2022' → '2022'. Always an integer.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exam, e.g. 'Examen 2024 exercise 3' → '3'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MATH-101e course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class MATH101eBot(DirectCourseBot):
    name = "MATH-101e"
    index = "course_math101e"
    groups = []
    tool_input_schema = ToolInput
