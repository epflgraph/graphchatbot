import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.compilers.evaluate import GradeEvaluateCompiler
from app.bots.explique.grade.state import GradeBotState
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def evaluate_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Infer the student's understanding state, or None when the evaluation failed."""
    student_state = await structured_call(
        bot=runtime.context,
        compiler=GradeEvaluateCompiler,
        state=state,
        fallback=None,
    )
    if student_state is not None:
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
