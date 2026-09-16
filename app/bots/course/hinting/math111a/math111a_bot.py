from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.bots.course.hinting.hinting_bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["theory"]] = Field(
        default=None,
        description="Optional subtype for theory content. 'theory' = general lecture notes / polycopié",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["exercise", "serie"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description=(
            "For 'serie': 'Série 13 exo 4' → '13'. For 'exercise': 'Question ouverte 4' → '4', "
            "'Question ouverte, ex 2' → '2'."
        ),
    )
    sub_number: Optional[str] = Field(
        default=None,
        description=(
            "The exercise number within the series; for 'serie' only, never for 'exercise'. "
            "'Série 2 exo 3' → number '2', sub_number '3'; 'Series 11 Exercise 1' → number '11', sub_number '1'."
        ),
    )

    @field_validator("number")
    @classmethod
    def _validate_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError("number must be digits, e.g. '5'")
        return v

    @field_validator("sub_number")
    @classmethod
    def _validate_sub_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError("sub_number must be digits, e.g. '3'")
        return v


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["exam"]] = Field(
        default=None,
        description="Optional subtype for exam content. 'exam' = final/general exams from past years.",
    )
    number: Optional[str] = Field(
        default=None,
        description=(
            "Year of the exam, e.g. 'Exam 2022' → '2022'; for an academic year like '2022/2023' use the first year. "
            "Always digits."
        ),
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exam, e.g. 'Examen 2024 Question 8' → '8'. Always digits.",
    )

    @field_validator("number")
    @classmethod
    def _validate_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not (v.isdigit() and len(v) == 4):
            raise ValueError("number must be a year, e.g. '2019'")
        return v

    @field_validator("sub_number")
    @classmethod
    def _validate_sub_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError("sub_number must be digits, e.g. '3'")
        return v


class ToolInput(BaseModel):
    """
    Search schema for MATH-111a course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class MATH111aBot(HintingCourseBot):
    name = "MATH-111a"
    index = "course_math111a"
    groups = []
    tool_input_schema = ToolInput
