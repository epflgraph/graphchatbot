from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.direct.direct_bot import DirectCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["video_lecture", "polycopie", "lecture_slides"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["exercice_sig", "exercice_geo", "quiz"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="""For 'exercice_sig': e.g. 'Exercice SIG Exercice 2' → '2'.
            For 'exercice_geo': e.g. 'Exercice GEO Exercice 1' → '1'.
            For 'quiz': e.g. 'Quiz 3.0.10' → '3.0.10'.""",
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["previous_year_exam"]] = Field(
        default=None,
        description="e.g. 'Examen 2019' → 'previous_year_exam'.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Year of the exam, e.g. 'Exam 2022' → '2022'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exam, e.g. 'mid-term 2024 Q15' → '15'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for ENV-342 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class ENV342Bot(DirectCourseBot):
    name = "ENV-342"
    index = "course_env342"
    groups = ["graph-chatbot-admins", "graph-rag-vip", "chatbot_env_342"]
    tool_input_schema = ToolInput
