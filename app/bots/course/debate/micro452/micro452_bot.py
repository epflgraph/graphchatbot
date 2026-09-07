import asyncio
import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.bots.course.debate.debate_bot import DebateCourseBot
from app.interfaces.graphai import graphai

logger = logging.getLogger(__name__)


class TheoryFilters(BaseModel):
    type: Literal["theory"] = "theory"
    subtype: Optional[Literal["theory", "theory_slides"]] = Field(
        default=None,
        description="Optional subtype for theory content. 'theory' = lecture notes / polycopié, 'theory_slides' = lecture slides.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"] = "practice"
    subtype: Optional[Literal["case_study"]] = Field(
        default=None,
        description="Subtype for practice content. 'case_study' = case-study documents.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Case study number in LNCM format, e.g. 'L3C2' for Lecture 3 Case study 2.",
    )
    is_solution: Optional[bool] = Field(
        default=None,
        description="False for the case-study question file, True for the solution and misconceptions files.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MICRO-452 case study material.
    """

    keywords: Optional[list[str]] = Field(
        default=None,
        description="Keywords to search for in the theory material.",
    )
    case_study_number: Optional[str] = Field(
        default=None,
        description="Case study number in LNCM format, e.g. 'L3C2' for Lecture 3 Case study 2.",
    )


class MICRO452DebateBot(DebateCourseBot):
    name = "MICRO-452-case-studies"
    index = "course_micro_452_case_studies"
    groups = []
    tool_input_schema = ToolInput

    async def search_course_material(
        self,
        keywords: Optional[list[str]] = None,
        case_study_number: Optional[str] = None,
    ) -> list:
        keywords = keywords or []
        logger.info(f"case_study_number={case_study_number!r}")

        if case_study_number:
            questions, solution_and_misconceptions, theory_result = await asyncio.gather(
                graphai.rag_retrieve(
                    index=self.index,
                    texts=keywords,
                    limit=9999,
                    filters=PracticeFilters(number=case_study_number, is_solution=False),
                ),
                graphai.rag_retrieve(
                    index=self.index,
                    texts=keywords,
                    limit=9999,
                    filters=PracticeFilters(number=case_study_number, is_solution=True),
                ),
                graphai.rag_retrieve(
                    index=self.index,
                    texts=keywords,
                    limit=5,
                    filters=TheoryFilters(subtype="theory_slides"),
                ),
            )
            result = questions + solution_and_misconceptions + theory_result
        else:
            result = await graphai.rag_retrieve(
                index=self.index,
                texts=[],
                limit=9999,
                filters=PracticeFilters(subtype="case_study", is_solution=False),
            )

        logger.info(f"Retrieved {len(result.chunks)} chunks.")

        return self._format_results(result)
