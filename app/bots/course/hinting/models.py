from pydantic import BaseModel, Field


class ExpandableSection(BaseModel):
    """A titled block that renders inside a <details> element."""

    title: str = Field(..., description="The text shown in the <summary> of the details block.")
    body: str = Field(..., description="The content inside the details block; may contain Markdown and LaTeX.")


class Hint(ExpandableSection):
    """One progressive hint."""


class Solution(ExpandableSection):
    """The final, complete answer."""


class HintingResponse(BaseModel):
    """A Socratic hinting response: an opening line, one or more hints, and a full solution."""

    opening: str = Field(..., description="A short opening sentence that frames the problem without giving the answer.")
    hints: list[Hint] = Field(..., description="One or more progressive hints, from least to most revealing.")
    solution: Solution = Field(..., description="The final, complete answer/solution.")
