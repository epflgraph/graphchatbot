from pathlib import Path
from typing import ClassVar, TypedDict

from app.bots.artifacts.base import Artifact
from app.bots.course.hinting.models import HintingResponse


class HintingResponseContext(TypedDict):
    course_name: str
    opening: str
    hints: list[dict[str, str]]
    solution: dict[str, str]


class HintingResponseArtifact(Artifact):
    """A hinting response rendered as expandable HTML sections."""

    TEMPLATE_DIR: ClassVar[Path] = Path(__file__).parent / "artifacts"
    TEMPLATE_NAME: ClassVar[str] = "hinting-response.html"

    course_name: str
    response: HintingResponse

    def _context(self) -> HintingResponseContext:
        return HintingResponseContext(
            course_name=self.course_name,
            opening=self.response.opening,
            hints=[hint.model_dump() for hint in self.response.hints],
            solution=self.response.solution.model_dump(),
        )
