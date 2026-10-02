from app.bots.explique.state import ExpliqueBotState
from app.bots.explique.train.models import ChallengePlan


class TrainBotState(ExpliqueBotState):
    """LangGraph state for explique tutor bots: the open-ended plan, and a filled practice request."""

    challenge_plan: ChallengePlan
    practice_response: str | None
