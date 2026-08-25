import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.compilers.summarize import SummarizeCompiler
from app.bots.explique.models import SessionSummary
from app.bots.explique.state import ExpliqueBotState
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def summarize_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Produce a total digest of the whole session for the end-of-session
    recap and feedback, via a structured-output call over the dialog history."""

    summary = await structured_call(
        bot=runtime.context,
        compiler=SummarizeCompiler,
        state=state,
        fallback=SessionSummary(),
    )

    logger.info(
        "Session summary: %d topic(s), %d strength(s), %d weakness(es)",
        len(summary.topics),
        len(summary.strengths),
        len(summary.weaknesses),
    )
    return {"session_summary": summary}
