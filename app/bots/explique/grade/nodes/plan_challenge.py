import asyncio
import hashlib
import json
import logging

from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime
from pydantic import TypeAdapter, ValidationError

from app.bots.base import Bot, StateUpdate
from app.bots.cache import points_applied as cache
from app.bots.cache.file_cache import CacheKey
from app.bots.explique.grade.compilers.plan_challenge import GradePlanChallengeCompiler
from app.bots.explique.grade.models import GradeChallengePlan
from app.bots.explique.grade.prompts import STATUS_PLANNING_TEMPLATE
from app.bots.explique.grade.state import GradeBotState
from app.bots.explique.grade.transcript import graded_history_per_turn
from app.bots.utils import announce
from app.compilation.invoke import structured_call
from app.logging_config import truncate

logger = logging.getLogger(__name__)

_POINTS_APPLIED_SCHEMA = TypeAdapter(list[str])


async def plan_challenge_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Plan the next tutoring move, and record progress against the topic's expected points."""
    announce(STATUS_PLANNING_TEMPLATE, runtime)
    bot = runtime.context
    all_points = state["topic_points"]
    topic_lock = state["topic_lock"]
    *past_turns, last_turn = graded_history_per_turn(
        bot.prompt_search_path, topic_lock.topic, state["messages"], topic_lock.position
    )

    applied_per_past_turn = await asyncio.gather(*(_points_applied_on(bot, state, turn) for turn in past_turns))
    past_points_applied = tuple(point for point in all_points if point in set().union(*applied_per_past_turn))
    progress = await structured_call(
        bot=bot,
        compiler=GradePlanChallengeCompiler,
        state={**state, "past_points_applied": past_points_applied},
        fallback=None,
    )

    if progress is None:
        points_remaining = tuple(point for point in all_points if point not in past_points_applied)
        logger.warning("Planner call failed; aiming the move at the next point not yet applied")
        return {
            "challenge_plan": GradeChallengePlan(
                points_applied=list(past_points_applied), points_remaining=list(points_remaining)
            ),
            "current_point": points_remaining[0] if points_remaining else past_points_applied[-1],
        }

    applied_on_last_turn = tuple(point for idx, point in enumerate(all_points, 1) if idx in progress.applied_points)
    cache.CACHE.put(_turn_cache_key(state, last_turn), json.dumps(applied_on_last_turn, ensure_ascii=False))
    points_applied = tuple(
        point for point in all_points if point in past_points_applied or point in applied_on_last_turn
    )
    points_remaining = tuple(point for point in all_points if point not in points_applied)

    next_point = all_points[progress.next_point - 1] if 1 <= progress.next_point <= len(all_points) else None
    # An applied point is a legal pick only once the topic is covered: there are no new
    # available points left, so the move stress-tests the weakest thing the student said instead.
    if next_point in points_applied and points_remaining:
        next_point = None

    if not next_point and progress.direction:
        logger.warning("Planner picked point %s and cannot be followed; dropping its direction", progress.next_point)

    logger.info(
        "Planned challenge applied=%s/%s (past %s); next=%r; direction=%s; reasoning=%s",
        len(points_applied),
        len(all_points),
        len(past_points_applied),
        next_point,
        truncate(progress.direction),
        truncate(progress.reasoning),
    )

    plan = GradeChallengePlan(
        points_applied=list(points_applied),
        reasoning=progress.reasoning if next_point else "",
        points_remaining=list(points_remaining),
        direction=progress.direction if next_point else "",
    )
    # Falls back to the course's own order when the pick could not be followed,
    # and on a covered topic to the last point claimed.
    fallback = points_remaining[0] if points_remaining else (points_applied[-1] if points_applied else "")
    current_point = next_point or fallback
    return {"challenge_plan": plan, "current_point": current_point}


async def _points_applied_on(bot: Bot, state: GradeBotState, turn: list[BaseMessage]) -> tuple[str, ...]:
    """The points the planner finds applied up to `turn`, scored once and then remembered."""
    key = _turn_cache_key(state, turn)
    cached_points = _cached_points_applied(key)
    if cached_points is not None:
        return cached_points

    logger.debug("Re-scoring a past turn missing from the cache")
    progress = await structured_call(
        bot=bot,
        compiler=GradePlanChallengeCompiler,
        state={**state, "messages": turn},
        fallback=None,
    )
    if progress is None:
        return ()
    points_applied = tuple(
        point for idx, point in enumerate(state["topic_points"], 1) if idx in progress.applied_points
    )
    cache.CACHE.put(key, json.dumps(points_applied, ensure_ascii=False))
    return points_applied


def _cached_points_applied(key: CacheKey) -> tuple[str, ...] | None:
    """The points cached as applied under `key`, or None on a miss or an unreadable entry."""
    cached_points = cache.CACHE.get(key)
    if cached_points is None:
        return None
    try:
        return tuple(_POINTS_APPLIED_SCHEMA.validate_json(cached_points))
    except ValidationError:
        logger.warning("Cached applied points at %s are not a list of strings; scoring the turn again", key.value)
        return None


def _turn_cache_key(state: GradeBotState, turn: list[BaseMessage]) -> CacheKey:
    """SHA-256 of the canonical JSON of the topic, its points, and the conversation up to `turn`."""
    conversation = [[message.type, message.content] for message in turn]  # not `id`, which varies per request
    dump = json.dumps(
        [state["topic_lock"].topic.name, state["topic_points"], conversation], sort_keys=True, ensure_ascii=True
    )
    return CacheKey(hashlib.sha256(dump.encode("utf-8")).hexdigest())
