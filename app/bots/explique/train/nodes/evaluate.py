import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.train.compilers.evaluate import EvaluateCompiler
from app.bots.explique.train.models import StudentState
from app.bots.explique.train.state import ExpliqueBotState
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def evaluate_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """
    Infer the student's understanding state from the conversation history, grounded in
    the source material retrieved this turn, via a structured-output LLM call.
    """
    student_state = await structured_call(
        bot=runtime.context,
        compiler=EvaluateCompiler,
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
