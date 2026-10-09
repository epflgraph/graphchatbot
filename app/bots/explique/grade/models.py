from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class GradeStudentIntent(StrEnum):
    """The intents only the grade classifier recognizes,
    on top of the `StudentIntent` ones."""

    JAILBREAK = "jailbreak"
    CLARIFICATION = "clarification"


class TopicPoints(BaseModel):
    """The points a student has to cover for a topic to count as explained."""

    reasoning: str = Field(
        default="",
        description="One or two sentences on what this topic's core content is. Internal — never shown to the student.",
    )
    points: list[str] = Field(
        default_factory=list,
        description="The topic's points, in the order a student would build them up.",
    )


class PointsProgress(BaseModel):
    """How far the student has got through the topic's expected points.

    Indices rather than prose: the points are already on the server, so quoting them back
    costs a paragraph a turn, and a number cannot name a point the course never set.
    """

    reasoning: str = Field(
        default="",
        description=(
            "One sentence: which points are applied, which are only stated, and why that "
            "one comes next. Never shown to the student."
        ),
    )
    applied_points: list[int] = Field(
        default_factory=list,
        description="The numbers of the expected points the student has applied, by position.",
    )
    next_point: int = Field(
        default=0,
        description=(
            "The number of the point to take up now, given what the student just said. "
            "One not yet in applied_points — or, once every point is applied, the one "
            "applied most weakly."
        ),
    )
    direction: str = Field(
        default="",
        description="How to take up next_point, in one short sentence.",
    )


class GradeChallengePlan(BaseModel):
    """What `plan_challenge` writes to state for the responder to read."""

    reasoning: str = ""
    points_applied: list[str] = Field(default_factory=list)
    points_remaining: list[str] = Field(default_factory=list)
    direction: str = ""

    @property
    def topic_exhausted(self) -> bool:
        """Whether the topic is covered: everything applied, nothing left."""
        # `points_applied` is checked too because a failed call falls back to both lists
        # empty, and a dropped request must not read as a finished topic.
        return bool(self.points_applied and not self.points_remaining)


class RevisionTopic(BaseModel):
    """A topic the student needs to revise: what to work on, and how they should ask about it."""

    next_step: str = Field(
        description=(
            "One sentence to the student, as 'you', in their language: the gap as something to work on next, "
            "never a verdict."
        ),
    )
    question: str = Field(
        description=(
            "The question the student would type into a course assistant to close this gap: first person, "
            "in their language. It names the concept outright, since the assistant has not seen this session."
        ),
    )

    @field_validator("next_step", "question")
    @classmethod
    def _collapse_whitespace(cls, value: str) -> str:
        return " ".join(value.split())


class Revision(BaseModel):
    """What a graded session left open, for the student to revise."""

    reasoning: str = Field(
        default="",
        description="One or two sentences on which gaps the session showed. Never shown to the student.",
    )
    points: list[RevisionTopic] = Field(
        default_factory=list,
        description=(
            "One per slip the student made in the session, recovered from or not. Empty when they made none; "
            "never something they simply did not mention."
        ),
    )
