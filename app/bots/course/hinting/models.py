from typing import Literal

from pydantic import BaseModel, Field


class ExpandableSection(BaseModel):
    """A titled block that renders inside a <details> element."""

    title: str = Field(..., description="The text shown in the <summary> of the details block.")
    body: str = Field(..., description="The content inside the details block; may contain Markdown and LaTeX.")


class Hint(ExpandableSection):
    """One progressive hint."""


class ResponseSection(BaseModel):
    """One piece of a hinting response: either a plain text paragraph or an expandable hint."""

    type: Literal["text", "hint"] = Field(
        ...,
        description="'text' for a paragraph the student sees immediately; 'hint' for an expandable guidance block.",
    )
    content: str = Field(..., description="The section content; may contain Markdown and LaTeX.")
    title: str | None = Field(
        default=None,
        description="Required when type is 'hint': the summary line of the expandable block.",
    )


class HintingResponse(BaseModel):
    """A unified response made of ordered text/hint sections.

    The LLM decides how to compose the response: a greeting can be a single text section,
    a practice problem can mix an opening text section with several hint sections, and a
    solution request can use text sections to explain the answer directly.
    """

    sections: list[ResponseSection] = Field(
        ...,
        description="Ordered list of paragraphs and/or expandable hints that make up the response.",
    )
