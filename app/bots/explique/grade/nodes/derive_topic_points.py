import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.prompts import STATUS_FETCHING_TEMPLATE
from app.bots.explique.grade.state import GradeBotState
from app.bots.explique.grade.topic_points import TopicPointsUnavailable, derive_topic_points
from app.bots.utils import announce

logger = logging.getLogger(__name__)


async def derive_topic_points_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """The points the locked topic has to cover, from the cache or derived on demand."""
    topic_lock = state["topic_lock"]
    if topic_lock is None or state["session_finished"]:
        return {}

    announce(STATUS_FETCHING_TEMPLATE, runtime)
    bot = runtime.context
    try:
        return {"topic_points": await derive_topic_points(bot, topic_lock.topic, state)}
    except TopicPointsUnavailable:
        logger.error("No points for topic %r in index %r", topic_lock.topic.name, bot.index)
        return {"topic_unavailable": True}
