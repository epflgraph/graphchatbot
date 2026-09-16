import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.compilers.plan_challenge import GradePlanChallengeCompiler
from app.bots.explique.grade.models import GradeChallengePlan, PointsProgress
from app.bots.explique.grade.prompts import STATUS_PLANNING_TEMPLATE
from app.bots.explique.grade.state import GradeBotState
from app.bots.utils import announce
from app.compilation.invoke import structured_call
from app.logging_config import truncate

logger = logging.getLogger(__name__)


async def plan_challenge_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Plan the next tutoring move, and record progress against the topic's expected points."""
    announce(STATUS_PLANNING_TEMPLATE, runtime)
    progress = await structured_call(
        bot=runtime.context,
        compiler=GradePlanChallengeCompiler,
        state=state,
        fallback=PointsProgress(),
    )

    all_points = state["topic_points"]
    applied_points = tuple(all_points[i - 1] for i in sorted(set(progress.applied_points)) if 1 <= i <= len(all_points))
    remaining_points = tuple(point for point in all_points if point not in applied_points)

    next_point = all_points[progress.next_point - 1] if 1 <= progress.next_point <= len(all_points) else None
    # An applied point is a legal pick only once the topic is covered: there are no new
    # available points left, so the move stress-tests the weakest thing the student said instead.
    if next_point in applied_points and remaining_points:
        next_point = None

    if not next_point and progress.direction:
        logger.warning("Planner picked point %s and cannot be followed; dropping its direction", progress.next_point)

    logger.info(
        "Planned challenge applied=%s/%s; next=%r; direction=%s; reasoning=%s",
        len(applied_points),
        len(all_points),
        next_point,
        truncate(progress.direction),
        truncate(progress.reasoning),
    )

    plan = GradeChallengePlan(
        points_applied=list(applied_points),
        reasoning=progress.reasoning if next_point else "",
        points_remaining=list(remaining_points),
        direction=progress.direction if next_point else "",
    )
    # Falls back to the course's own order when the pick could not be followed,
    # and on a covered topic to the last point claimed.
    fallback = remaining_points[0] if remaining_points else (applied_points[-1] if applied_points else "")
    current_point = next_point or fallback
    return {"challenge_plan": plan, "current_point": current_point}
