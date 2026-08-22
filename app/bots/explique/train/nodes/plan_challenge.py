import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.train.compilers.plan_challenge import PlanChallengeCompiler
from app.bots.explique.train.models import ChallengePlan
from app.bots.explique.train.state import ExpliqueBotState
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def plan_challenge_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Plan the next teaching move from the transcript so far."""
    plan = await structured_call(
        bot=runtime.context,
        compiler=PlanChallengeCompiler,
        state=state,
        fallback=ChallengePlan(),
    )

    logger.info(
        "Planned challenge direction=%r; points_tested=%r; reasoning=%s",
        plan.direction,
        plan.points_tested,
        plan.reasoning,
    )

    return {"challenge_plan": plan}
