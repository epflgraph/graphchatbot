import asyncio
import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_serializer

from app.bots.course.debate.debate_bot import DebateCourseBot
from app.interfaces.graphai import graphai

logger = logging.getLogger(__name__)


class TheoryFilters(BaseModel):
    type: Literal["theory"] = "theory"
    subtype: Optional[Literal["lecture_slides"]] = None


class CaseStudyFilters(BaseModel):
    type: Literal["case_study"] = "case_study"
    week: int = 1
    number: Optional[int] = None
    subtype: Optional[Literal["question"]] = None

    @field_serializer("number")
    def serialize_number(self, number: int) -> str:
        return str(number)


class ToolInput(BaseModel):
    """
    Search schema for MICRO-452 case study material.
    """

    keywords: Optional[list[str]] = Field(
        default=None,
        description="Keywords to search for in the theory material. Ignored when case_study_number is not provided.",
    )
    case_study_number: Optional[int] = Field(
        default=None,
        description="Number of the case study to retrieve in full. Omit to list all available case studies.",
    )


class MICRO452DebateBot(DebateCourseBot):
    name = "MICRO-452-case-studies"
    index = "course_micro_452_case_studies"
    groups = ["graph-chatbot-admins", "graph-rag-vip", "MICRO-452-admin", "MICRO-452-case-studies"]
    tool_input_schema = ToolInput

    async def search_course_material(
        self,
        keywords: Optional[list[str]] = None,
        case_study_number: Optional[int] = None,
    ) -> list:
        keywords = keywords or []
        logger.info(f"case_study_number={case_study_number!r}")

        if case_study_number:
            case_study_result, theory_result = await asyncio.gather(
                graphai.rag_retrieve(
                    index=self.index,
                    texts=keywords,
                    limit=9999,
                    filters=CaseStudyFilters(number=case_study_number),
                ),
                graphai.rag_retrieve(
                    index=self.index,
                    texts=keywords,
                    limit=5,
                    filters=TheoryFilters(subtype="lecture_slides"),
                ),
            )
            result = case_study_result + theory_result
        else:
            result = await graphai.rag_retrieve(
                index=self.index,
                texts=keywords,
                limit=9999,
                filters=CaseStudyFilters(subtype="question"),
            )

        logger.info(f"Retrieved {len(result.chunks)} chunks.")

        return self._format_results(result)
