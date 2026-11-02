import re
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.course_bot import CATEGORIES, RequestType
from app.bots.course.direct.direct_bot import DirectCourseBot
from app.interfaces.graphai import RAGResult

# Cards open with a YAML frontmatter block (`id: K05.01`, `related: …`) whose
# identifiers participants have no access to.
_LEADING_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n+", re.DOTALL)


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["sources", "corpus"]] = Field(
        default=None,
        description="Optional subtype for theory content. Chunks coming from raw, original sources have subtype `sources`. A set of 109 knowledge cards, covering the general research process, the specific thesis project (SIP) and its evaluation have subtype `corpus`.",
    )


class ToolInput(BaseModel):
    """
    Search schema for EMBA-SIP course material.
    Keep queries concise (≤ 15 words).
    """

    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


class EMBASIPBot(DirectCourseBot):
    name = "EMBA-SIP"
    index = "course_emba"
    groups = []
    tool_input_schema = ToolInput
    content_language = "en"

    # The knowledge base holds the program's rules and evaluation criteria
    # (A and E cards), so admin requests must search it like theory requests.
    CATEGORIES = CATEGORIES | {
        RequestType.ADMIN: {
            "description": "The user's request is about the program's rules and practicalities of the SIP, like deliverables, deadlines, supervision, confidentiality, academic integrity, or the defense.",
            "tool_choice": "any",
        },
    }

    @classmethod
    def _format_results(cls, result: RAGResult) -> list[dict]:
        formatted = super()._format_results(result)
        # The `number` field and the cards' leading YAML frontmatter hold the
        # cards' internal identifiers (e.g. "K05.01"). Participants have no
        # access to the cards, so citing them tells them nothing — drop the
        # identifiers instead of asking the model to ignore them.
        return [
            {
                key: _LEADING_FRONTMATTER.sub("", value) if key == "content" and isinstance(value, str) else value
                for key, value in item.items()
                if key != "number"
            }
            for item in formatted
        ]
