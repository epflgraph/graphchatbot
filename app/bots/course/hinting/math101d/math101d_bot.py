from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.hinting.hinting_bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["theory", "theory_slides", "mediaspace_video"]] = Field(
        default=None,
        description="Optional subtype for theory content. 'theory' = polycopié and course handouts, 'theory_slides' = weekly lecture notes ('Notes Semaine N'), 'mediaspace_video' = lecture recordings.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["serie", "homework"]] = Field(
        default=None,
        description="Optional subtype for practice content. 'serie' = weekly exercise series, 'homework' = graded exercise to hand in (exercice à rendre).",
    )
    number: Optional[int] = Field(
        default=None,
        description="Series or homework number, without leading zeros, e.g. 'Série 13 exo 4' → 13, 'S02' → 2, 'exercice rendu 1' → 1.",
    )
    sub_number: Optional[int] = Field(
        default=None,
        description="Exercise number within the series, ignoring any letter, e.g. 'Série 2 exo 3f' → 3; for 'serie' only, never for 'homework'.",
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["midterm_exam"]] = Field(
        default=None,
        description="Optional subtype for exam content. 'midterm_exam' = the examen blanc (mock midterm).",
    )
    number: Optional[int] = Field(
        default=None,
        description="Which exam: the midterm ('examen blanc', 'midterm') → 1; a past exam by its year, e.g. 'Examen 2022' → 2022.",
    )
    sub_number: Optional[int] = Field(
        default=None,
        description="Question number within the exam, ignoring any letter, e.g. 'examen blanc question 6b' → 6, 'mock midterm Q3' → 3.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MATH-101d course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class MATH101dBot(HintingCourseBot):
    name = "MATH-101d"
    index = "course_math101d"
    groups = []
    tool_input_schema = ToolInput
