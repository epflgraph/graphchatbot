from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.hinting.hinting_bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["theory", "theory_slides", "mediaspace_video"]] = Field(
        default=None,
        description="Optional subtype for theory content. 'theory' = general lecture notes / polycopié, 'theory_slides' = lecture slides, 'mediaspace_video' = course videos.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["serie", "homework"]] = Field(
        default=None,
        description="Optional subtype for practice content. 'serie' = weekly exercise series, 'homework' = exercise to hand in (exercice / question à rendre).",
    )
    number: Optional[int] = Field(
        default=None,
        description="Series or homework number, e.g. 'Série 13 exo 4' → 13, 'S02' → 2, 'question à rendre 2' → 2.",
    )
    sub_number: Optional[int] = Field(
        default=None,
        description=(
            "Exercise number within the series, ignoring any letter; for 'serie' only, never for 'homework'. "
            "'Série 2 exo 3f' → number 2, sub_number 3; 'Series 11 Exercise 1b' → number 11, sub_number 1."
        ),
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["midterm_exam"]] = Field(
        default=None,
        description="Optional subtype for exam content. 'midterm_exam' = the midterm (examen blanc).",
    )
    number: Optional[int] = Field(
        default=None,
        description="Which exam: the midterm ('examen blanc', 'midterm') → 1; a past exam by its year, e.g. 'Examen 2022' → 2022.",
    )
    sub_number: Optional[int] = Field(
        default=None,
        description="Question number within the exam, ignoring any letter, e.g. 'examen blanc question 8b' → 8.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MATH-111e course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class MATH111eBot(HintingCourseBot):
    name = "MATH-111e"
    index = "course_math111e"
    groups = []
    tool_input_schema = ToolInput
