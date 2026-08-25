import logging
from typing import Literal

from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from app.bots.base import Bot, BotState, StateUpdate
from app.bots.languages import LANGUAGES, UNDETERMINED
from app.compilation.base import MessageCompiler
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


class LanguageDetection(BaseModel):
    """The language a user is writing in."""

    reasoning: str = Field(
        default="",
        description=(
            "One short sentence: which language the latest user's turn is written in, and — "
            "when the message is too thin to carry one — what can be inferred from the conversation history."
        ),
    )
    lang_code: Literal[*LANGUAGES, UNDETERMINED] = Field(
        default=UNDETERMINED,
        description=f"The turn's ISO 639-1 code, or `{UNDETERMINED}` when no supported language can be inferred.",
    )


def make_detect_language_node(compiler: type[MessageCompiler]):
    """Returns a node that infers the user's language from their latest turn.

    `lang_code` is read from `compiler`'s schema and written to state, so both
    have to declare it.
    """

    async def detect_language_node(state: BotState, runtime: Runtime[Bot]) -> StateUpdate:
        detection = await structured_call(
            bot=runtime.context,
            compiler=compiler,
            state=state,
            fallback=LanguageDetection(),
        )

        logger.info("Detected language: lang_code=%r; reasoning=%s", detection.lang_code, detection.reasoning)

        return {"lang_code": detection.lang_code if detection.lang_code in LANGUAGES else None}

    return detect_language_node
