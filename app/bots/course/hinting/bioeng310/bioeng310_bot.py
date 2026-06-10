from typing import Annotated, Literal, Optional, Union

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.bots.course.hinting.hinting_bot import HintingCourseBot
from app.config import config


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "recommended_reading"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["exercise"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="The week number, e.g. 'Week 1' → '1'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="The lecture number followed by the exercise number, e.g. 'Week 1, Exercises Lecture 2, Ex 7' → '2.7'.",
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["exam_example"]] = Field(
        default=None,
        description="Optional subtype, e.g. 'Exam 2019' → 'exam_example'.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Year of the exam, e.g. 'Exam 2022' → '2022'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exam, e.g. 'Exam 2024 Q15' → '15'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for BIOENG-310 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """
    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class BIOENG310Bot(HintingCourseBot):
    name = 'BIOENG-310'
    index = 'course_bioeng310'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'chatbot_bioeng_310']
    tool_input_schema = ToolInput

    model = ChatOpenAI(
        base_url=config.get("rcp", {})["base_url"],
        model="Qwen/Qwen3-30B-A3B-Instruct-2507",
        api_key=config.get("rcp", {})["api_key"],
        timeout=60,
        stream_usage=True,
    )

    light_model = model
