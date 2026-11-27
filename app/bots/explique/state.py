from app.bots.base import BotState
from app.bots.explique.models import RejectedResponse, SessionSummary, StudentState, TutorAction


class ExpliqueBotState(BotState):
    """LangGraph state all explique flavours write."""

    student_state: StudentState | None
    tutor_action: TutorAction
    session_summary: SessionSummary

    # The candidate reply `respond` generated this turn, held out of `messages` until
    # the response evaluator clears it — a rejected one must never reach the stream.
    candidate_response: str | None
    # What of the `candidate_response` hasn't reached the student yet,
    # streamed once it is accepted; None when `respond` did not stream.
    not_streamed_response: str | None
    rejected_responses: tuple[RejectedResponse, ...]
