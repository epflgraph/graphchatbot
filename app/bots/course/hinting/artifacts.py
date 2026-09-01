from pathlib import Path
from typing import ClassVar, TypedDict

from app.bots.artifacts.base import Artifact
from app.bots.course.hinting.models import HintingResponse


class HintingResponseContext(TypedDict):
    course_name: str
    sections: list[dict[str, str]]


class HintingResponseArtifact(Artifact):
    """A hinting response rendered as expandable Markdown sections."""

    TEMPLATE_DIR: ClassVar[Path] = Path(__file__).parent / "artifacts"
    TEMPLATE_NAME: ClassVar[str] = "hinting-response.md"
    AUTOESCAPE: ClassVar[bool] = False

    course_name: str
    response: HintingResponse

    def _context(self) -> HintingResponseContext:
        return HintingResponseContext(
            course_name=self.course_name,
            sections=[section.model_dump() for section in self.response.sections],
        )
