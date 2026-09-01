from app.bots.course.compilers.respond import GroundedResponseCompiler
from app.bots.course.hinting.models import HintingResponse


class HintingResponseCompiler(GroundedResponseCompiler):
    """Unified hinting response compiler.

    The model fills a single `HintingResponse` schema made of ordered text/hint
    sections plus an optional solution. The respond node then either renders the
    Markdown artifact (when hints or a solution are present) or returns plain
    text directly (when only text sections are needed).
    """

    config = GroundedResponseCompiler.config.model_copy(
        update={
            "system_template": "respond-sys.md",
            "output_schema": HintingResponse,
        }
    )
