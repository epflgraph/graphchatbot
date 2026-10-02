import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.completion import session_finished
from app.bots.explique.grade.state import GradeBotState
from app.bots.explique.grade.topic_lock import find_topic_lock

logger = logging.getLogger(__name__)


async def lock_topic_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Everything a turn knows before it routes: the course's topics, the topic locked so
    far, and whether the exercise is already closed."""
    bot = runtime.context
    topics = bot.topics
    if not topics:
        logger.warning(
            "No quiz in course %s carries a topic tag, or no polling happened yet; %r has no menu to offer",
            bot.course_id,
            bot.name,
        )

    topic_lock = find_topic_lock(bot.prompt_search_path, topics, state["messages"])
    if topic_lock and topic_lock.is_in_latest_turn(state["messages"]):
        logger.info("Topic locked: %s", topic_lock.topic.name)
    return {
        "topic_lock": topic_lock,
        "topics": topics,
        "session_finished": session_finished(bot.prompt_search_path, state["messages"]),
    }
