import logging
from collections.abc import Callable

from app.bots.base import StateUpdate
from app.bots.explique.models import StudentState, TutorAction
from app.bots.explique.state import ExpliqueBotState

logger = logging.getLogger(__name__)


def make_select_action_node(select_tutor_action: Callable[[StudentState], TutorAction]):
    """Returns a node that picks the tutor's move from the evaluated student state, by the given rules."""

    async def select_action_node(state: ExpliqueBotState) -> StateUpdate:
        if state["student_state"] is None:
            logger.warning("No student state to select a tutor action from")
            return {}
        action = select_tutor_action(state["student_state"])
        logger.info("Selected tutor action=%r", action)
        return {"tutor_action": action}

    return select_action_node
