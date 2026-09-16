import functools
import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.models import StudentState
from app.bots.explique.state import ExpliqueBotState
from app.compilation.base import MessageCompiler
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def _evaluate_node(
    compiler: type[MessageCompiler], state: ExpliqueBotState, runtime: Runtime[Bot]
) -> StateUpdate:
    """
    Infer the student's understanding state from the conversation history, grounded in
    the source material retrieved this turn, via a structured-output LLM call.
    """
    student_state = await structured_call(
        bot=runtime.context,
        compiler=compiler,
        state=state,
        fallback=StudentState(),
    )

    logger.info(
        "Evaluated Student State: mastery=%r; gap_severity=%r; gap_type=%r; persistence=%r; engagement_level=%r; "
        "suspected_misconceptions=%r; reasoning=%s",
        student_state.mastery,
        student_state.gap_severity,
        student_state.gap_type,
        student_state.persistence,
        student_state.engagement_level,
        student_state.suspected_misconceptions,
        student_state.reasoning,
    )

    return {"student_state": student_state}


def make_evaluate_node(compiler: type[MessageCompiler]):
    """Returns a node that evaluates the student through `compiler`, so an
    explique flavour can read the conversation its own way."""
    return functools.partial(_evaluate_node, compiler)
