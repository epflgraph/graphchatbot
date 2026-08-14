from app.bots.base import BotState
from app.bots.explique.models import ChallengePlan, SessionSummary, StudentState
from app.bots.explique.tutor_action import TutorAction


class ExpliqueBotState(BotState):
    """LangGraph state for explique tutor bots."""

    student_state: StudentState
    tutor_action: TutorAction
    session_summary: SessionSummary
    challenge_plan: ChallengePlan

    practice_response: str | None
    # Dynamic routing: `tools` reads this to know where to send control back to
    active_node: str | None
    retrieval_round: int
