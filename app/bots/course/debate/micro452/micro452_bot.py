import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.bots.course.debate.debate_bot import DebateCourseBot
from app.interfaces.graphai import graphai

logger = logging.getLogger(__name__)


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
    name = 'MICRO-452-case-studies'
    index = 'course_micro_452_case_studies'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'MICRO-452-admin', 'MICRO-452-case-studies']
    tool_input_schema = ToolInput

    async def search_course_material(
        self,
        keywords: Optional[list[str]] = None,
        case_study_number: Optional[int] = None,
    ) -> list:
        keywords = keywords or []
        logger.info(f"keywords={keywords!r} case_study_number={case_study_number!r}")

        if case_study_number:
            case_study_results = await graphai.rag_retrieve(
                index=self.index,
                texts=keywords,
                limit=9999,
                filters={'type': 'case_study', 'week': 1, 'number': str(case_study_number)},
            )
            theory_results = await graphai.rag_retrieve(
                index=self.index,
                texts=keywords,
                limit=5,
                filters={'type': 'theory', 'subtype': 'lecture_slides'},
            )
            results = case_study_results + theory_results
        else:
            results = await graphai.rag_retrieve(
                index=self.index,
                texts=keywords,
                limit=9999,
                filters={'type': 'case_study', 'week': 1, 'subtype': 'question'},
            )

        logger.info(f"Retrieved {len(results)} chunks.")

        return [
            {k: v for k, v in {
                'type': f"{r.get('type')}: {r.get('subtype')}",
                'title': r.get('title'),
                'number': r.get('number'),
                'url': r.get('original_link'),
                'page': r.get('page'),
                'position': r.get('position'),
                'content.fr': r.get('content.fr'),
                'content.en': r.get('content.en'),
                'associated_video_lectures': [
                    {'title': v.get('title'), 'url': v.get('original_link')}
                    for v in (r.get('associated_video_lectures') or [])
                ] or None,
            }.items() if v is not None}
            for r in results
        ]
