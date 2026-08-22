import logging

from app.bots.base import StateUpdate
from app.bots.explique.train.state import ExpliqueBotState
from app.bots.explique.train.tutor_action import select_tutor_action

logger = logging.getLogger(__name__)


async def select_action_node(state: ExpliqueBotState) -> StateUpdate:
    """Deterministically select the tutor's pedagogical move from the inferred
    student state."""

    action = select_tutor_action(state["student_state"])
    logger.info("Selected tutor action=%r", action)

    return {"tutor_action": action}
