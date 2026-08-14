import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.compilers import COMPILERS
from app.bots.explique.compilers.base import ExpliqueTask
from app.bots.explique.models import StudentState
from app.bots.explique.state import ExpliqueBotState
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def evaluate_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """
    Infer the student's understanding state from the conversation history, grounded in
    the source material retrieved this turn, via a structured-output LLM call.
    """
    student_state = await structured_call(
        bot=runtime.context,
        compiler=COMPILERS.get(ExpliqueTask.EVALUATE),
        state=state,
        fallback=StudentState(),
    )
    return {"student_state": student_state}
