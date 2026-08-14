from app.bots.base import StateUpdate
from app.bots.explique.state import ExpliqueBotState
from app.bots.explique.tutor_action import select_tutor_action


async def select_action_node(state: ExpliqueBotState) -> StateUpdate:
    """Deterministically select the tutor's pedagogical move from the inferred
    student state."""

    return {"tutor_action": select_tutor_action(state["student_state"])}
