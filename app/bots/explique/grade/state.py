from app.bots.explique.grade.models import GradeChallengePlan, Revision
from app.bots.explique.grade.topic_lock import TopicLock
from app.bots.explique.grade.topics import Topics
from app.bots.explique.state import ExpliqueBotState


class GradeBotState(ExpliqueBotState):
    """LangGraph state for explique grade bots."""

    topics: Topics
    topic_lock: TopicLock | None
    topic_points: tuple[str, ...]
    topic_unavailable: bool
    session_finished: bool
    challenge_plan: GradeChallengePlan
    current_point: str
    revision: Revision
