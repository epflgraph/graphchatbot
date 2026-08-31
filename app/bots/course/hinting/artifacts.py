from pathlib import Path
from typing import ClassVar, TypedDict

from app.bots.artifacts.base import Artifact
from app.bots.course.hinting.models import HintingResponse


class HintingResponseContext(TypedDict):
    course_name: str
    opening: str
    hints: list[dict[str, str]]
    solution: dict[str, str]
    include_solution: bool


class HintingResponseArtifact(Artifact):
    """A hinting response rendered as expandable HTML sections.

    The model always produces a `solution` field so it has a dedicated place for
    the answer, but the rendered HTML only shows the solution when the course
    bot sets `include_solution=True`.
    """

    TEMPLATE_DIR: ClassVar[Path] = Path(__file__).parent / "artifacts"
    TEMPLATE_NAME: ClassVar[str] = "hinting-response.html"

    course_name: str
    response: HintingResponse
    include_solution: bool = True

    def _context(self) -> HintingResponseContext:
        return HintingResponseContext(
            course_name=self.course_name,
            opening=self.response.opening,
            hints=[hint.model_dump() for hint in self.response.hints],
            solution=self.response.solution.model_dump(),
            include_solution=self.include_solution,
        )
