from app.bots.course.compilers.respond import GroundedResponseCompiler
from app.bots.course.hinting.models import HintingResponse


class HintingResponseCompiler(GroundedResponseCompiler):
    """Structured hinting response: opening, hints, and a solution.

    The model fills a `HintingResponse` schema, which is then rendered into an
    HTML artifact by the respond node. The system prompt is shared with the
    plain-text compiler; only this user template adds the JSON schema.
    """

    config = GroundedResponseCompiler.config.model_copy(
        update={
            "system_template": "respond-hints-sys.md",
            "output_schema": HintingResponse,
        }
    )


class HintingPlainTextCompiler(GroundedResponseCompiler):
    """Plain-text answer for hinting bots when structured hints are not needed
    (greetings, admin, unrelated, or immediate factual questions).
    """

    config = GroundedResponseCompiler.config.model_copy(update={"system_template": "respond-text-sys.md"})
