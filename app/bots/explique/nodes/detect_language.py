import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.compilers import COMPILERS
from app.bots.explique.compilers.base import ExpliqueTask
from app.bots.explique.languages import LANGUAGES
from app.bots.explique.models import LanguageDetection
from app.bots.explique.state import ExpliqueBotState
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def detect_language_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """
    Detect the language the student is writing in from their latest turn, so the responder is
    told it outright instead of inferring it while writing the reply.
    """
    detection = await structured_call(
        bot=runtime.context,
        compiler=COMPILERS.get(ExpliqueTask.DETECT_LANGUAGE),
        state=state,
        fallback=LanguageDetection(),
    )

    logger.info("Detected language: lang_code=%r; reasoning=%s", detection.lang_code, detection.reasoning)

    return {"lang_code": detection.lang_code if detection.lang_code in LANGUAGES else None}
