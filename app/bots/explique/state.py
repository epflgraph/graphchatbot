from app.bots.base import BotState
from app.bots.explique.models import RejectedResponse, SessionSummary, StudentState, TutorAction


class ExpliqueBotState(BotState):
    """LangGraph state all explique flavours write."""

    student_state: StudentState
    tutor_action: TutorAction
    session_summary: SessionSummary

    # The language to reply in, read from the student's latest turn; None when none
    # could be read, which leaves the responder to infer it.
    lang_code: str | None

    # The candidate reply `respond` generated this turn, held out of `messages` until
    # the response evaluator clears it — a rejected one must never reach the stream.
    candidate_response: str | None
    # What of the `candidate_response` hasn't reached the student yet,
    # streamed once it is accepted; None when `respond` did not stream.
    not_streamed_response: str | None
    rejected_responses: tuple[RejectedResponse, ...]
