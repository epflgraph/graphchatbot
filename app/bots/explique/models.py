import logging
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from app.bots.explique.response_evaluator import EvaluationTag

logger = logging.getLogger(__name__)


class StudentIntent(StrEnum):
    """Intent categories produced by the explique classifier."""

    CHIT_CHAT = "chit-chat"
    OFF_TOPIC = "off-topic"
    NEW_TOPIC = "new-topic"
    SKIP_TOPIC = "skip-topic"
    IN_TOPIC_RESPONSE = "in-topic-response"
    REQUEST_PRACTICE = "request-practice"
    END_SESSION = "end-session"


class MessageEvent(StrEnum):
    """A `category` value the graph assigns itself, for cases that aren't a
    student intent — e.g. a turn whose content couldn't be read."""

    CONTENT_UNREADABLE = "content-unreadable"


class GapSeverity(StrEnum):
    """How large the gap in the student's understanding is."""

    LARGE = "large"
    PARTIAL = "partial"


class GapType(StrEnum):
    """The kind of gap in the student's understanding."""

    TRANSIENT = "transient"
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    LOGICAL = "logical"
    BIAS = "bias"
    DOMAIN = "domain"


class EngagementLevel(StrEnum):
    """How engaged the student is in the conversation."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Persistence(StrEnum):
    """How stuck the student is on the current point."""

    FRESH = "fresh"
    STUCK = "stuck"
    STALLED = "stalled"


class TutorAction(StrEnum):
    """The next pedagogical move a tutor can make."""

    MOTIVATE = "motivate"
    PROBE = "probe"
    HINT = "hint"
    EXPLAIN = "explain"
    CHALLENGE_MISCONCEPTION = "challenge-misconception"
    CHALLENGE_MASTERY = "challenge-mastery"


class StudentState(BaseModel):
    """
    Snapshot of the student's understanding state at a single exchange.

    These dimensions are inferred from the conversation history and any retrieved
    reference material. They remain internal to the backend.
    """

    reasoning: str = Field(
        default="",
        description=(
            "Written first, before every other field: a brief assessment that "
            "justifies the values below. Internal — never shown to the student."
        ),
    )
    mastery: bool = Field(
        default=False,
        description="True if the student's explanation is correct and complete.",
    )
    suspected_misconceptions: list[str] = Field(
        default_factory=list,
        description=(
            "Specific suspected misconceptions about the point under discussion, "
            "each phrased as a concrete confusion (e.g. 'confuses virtual dispatch "
            "with compile-time overloading'), never a bare category. At most two, "
            "and empty when mastery is true."
        ),
    )
    gap_severity: GapSeverity | None = Field(
        default=GapSeverity.PARTIAL,
        description="null if mastery is true; otherwise large or partial.",
    )
    gap_type: GapType | None = Field(
        default=GapType.TRANSIENT,
        description="null if mastery is true; otherwise transient, conceptual, procedural, logical, bias, or domain.",
    )
    engagement_level: EngagementLevel = Field(
        default=EngagementLevel.MEDIUM,
        description="high, medium, or low.",
    )
    persistence: Persistence = Field(
        default=Persistence.FRESH,
        description=(
            "How stuck the student is on the current point, judged from genuine "
            "reasoning attempts rather than their claims. Ignored when mastery is true."
        ),
    )

    @model_validator(mode="after")
    def _normalize_gap_state(self) -> Self:
        """Keep mastery consistent with the gap fields and suspected misconceptions."""

        if self.mastery:
            self.gap_severity = None
            self.gap_type = None
            self.suspected_misconceptions = []
        else:
            self.gap_severity = self.gap_severity or GapSeverity.PARTIAL
            self.gap_type = self.gap_type or GapType.TRANSIENT

        return self


class QuizQuestion(BaseModel):
    """One practice question, matching the client-side schema in `artifacts/practice-quiz.html`."""

    MIN_OPTIONS: ClassVar[int] = 2

    question: str = Field(min_length=1, description="The question text, plain text.")
    options: list[str] = Field(
        description=f"At least {MIN_OPTIONS} plausible answer choices, plain text; exactly one is correct.",
    )
    explanation: str = Field(
        default="",
        description=(
            "One or two sentences establishing which option is correct and why, written "
            "as the student will read it — not a scratch-pad thought process."
        ),
    )
    correct_idx: int = Field(description="Zero-based index into `options` of the option named in `explanation`.")

    @property
    def is_answerable(self) -> bool:
        return len(self.options) >= self.MIN_OPTIONS and 0 <= self.correct_idx < len(self.options)


class QuizQuestions(BaseModel):
    """The questions of one practice quiz."""

    SUMMARY: ClassVar[str] = "[A practice quiz was shown to the student, covering:\n{questions}\n]"
    EMPTY_SUMMARY: ClassVar[str] = "[A practice quiz was shown to the student.]"

    questions: list[QuizQuestion] = Field(default_factory=list)

    def to_summary(self) -> str:
        """The questions only, standing in for the rendered quiz markup in a transcript."""
        if not self.questions:
            logger.warning("Practice-quiz marker carries no questions; summarising it to a placeholder")
            return self.EMPTY_SUMMARY

        return self.SUMMARY.format(questions="\n".join(f"- {q.question}" for q in self.questions))


class QuizConfig(BaseModel):
    """A quiz page's content — everything `Quiz.render` needs beyond the questions themselves."""

    course_name: str
    title: str
    subtitle: str


class SessionSummary(BaseModel):
    """
    Faithful, total digest of one tutoring session, produced at end-of-session.

    Internal: the responder's source of truth for the recap and feedback, and never
    shown to the student. It is judged only from the work shown in the session, never
    from the student as a person, and never speculates beyond the transcript.
    """

    reasoning: str = Field(
        default="",
        description="Written first: a brief holistic read of how the session went, "
        "justifying the fields below. Internal.",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Every topic the student genuinely worked through, in order, each "
        "with what they came to understand about it — this is what makes the recap total, "
        "not just the last exchange. Real points only, not every micro-step. Empty if "
        "they barely engaged.",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="What they did well as a learner — specific, earned, process/effort "
        "not fixed traits ('kept going after a wrong turn', 'caught their own error'; "
        "never 'is smart'). Genuine ones only; leave empty rather than inflate.",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Concepts still not solid — candid here, but each phrased as something "
        "to revisit / a next step, not a verdict on the student. Only real gaps shown in "
        "the session; do not manufacture them.",
    )


class RejectedResponse(BaseModel):
    """A response the evaluator turned down, and what it found."""

    model_config = ConfigDict(frozen=True)

    response: str
    tag: EvaluationTag
