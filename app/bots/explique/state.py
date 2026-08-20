from app.bots.base import BotState
from app.bots.explique.models import ChallengePlan, RejectedResponse, SessionSummary, StudentState
from app.bots.explique.tutor_action import TutorAction


class ExpliqueBotState(BotState):
    """LangGraph state for explique tutor bots."""

    student_state: StudentState
    tutor_action: TutorAction
    session_summary: SessionSummary
    challenge_plan: ChallengePlan

    practice_response: str | None
    # The language to reply in, read from the student's latest turn; None when none
    # could be read, which leaves the responder to infer it.
    lang_code: str | None

    # The candidate reply `respond` generated this turn, held out of `messages` until
    # the response evaluator clears it — a rejected one must never reach the stream.
    candidate_response: str | None
    rejected_responses: tuple[RejectedResponse, ...]
