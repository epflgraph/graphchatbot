import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.compilers.revision import GradeRevisionCompiler
from app.bots.explique.grade.models import Revision
from app.bots.explique.grade.state import GradeBotState
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def revision_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    revision = await structured_call(
        bot=runtime.context,
        compiler=GradeRevisionCompiler,
        state=state,
        fallback=Revision(),
    )

    logger.info("Revision points: %d", len(revision.points))
    num_incomplete = sum(1 for point in revision.points if not (point.next_step and point.question))
    if num_incomplete:
        logger.warning("%d revision point(s) came back blank, left out or listed without a review link", num_incomplete)
    return {"revision": revision}
