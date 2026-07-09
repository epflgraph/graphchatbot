from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.direct.direct_bot import DirectCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "polycopie", "resume", "proof", "recommended_reading"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["serie", "serie_entrainement", "qcm"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="When subtype is 'serie' or 'serie_entrainement': serie number N. When subtype is 'qcm': e.g. 'QCM Q3' → 'Q3'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="When subtype is 'serie': exercise number, e.g. 'Série 3 Exercice 4' → '4'. When subtype is 'serie_entrainement': always N.M format, e.g. 'exo 3.1' → '3.1'.",
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["previous_year_exam", "mock_exam"]] = Field(
        default=None,
        description="e.g. 'Examen 2019' → 'previous_year_exam', 'Test blanc' → 'mock_exam'.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Year of the exam, e.g. 'Exam 2022' → '2022'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exam, e.g. 'Examen 2024 Q15' → '15'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MATH-106(e) course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """
    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class MATH106eBot(DirectCourseBot):
    name = 'MATH-106e'
    index = 'course_math106e'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'chatbot_math_106_e']
    tool_input_schema = ToolInput
