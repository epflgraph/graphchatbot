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


class ChallengePlan(BaseModel):
    """The next untested direction for a topic, planned speculatively alongside evaluation."""

    points_tested: list[str] = Field(
        default_factory=list,
        description=(
            "Every distinct point already raised with the student, phrased "
            "mechanism-agnostically so the same point raised in different words is "
            "still listed once. Empty on the first exchange on this topic."
        ),
    )
    reasoning: str = Field(
        default="",
        description=(
            "One short sentence explaining why this direction comes next. Internal — never shown to the student."
        ),
    )
    direction: str = Field(
        default="",
        description=(
            "The tutor's next move, as substance and target only — never tone or "
            "delivery, which is decided downstream. Set to exactly 'topic appears "
            "exhausted' once every point has been tested."
        ),
    )


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


class PracticeMaterial(BaseModel):
    """Structured output for a practice-material request."""

    MAX_QUESTIONS: ClassVar[int] = 10

    reasoning: str = Field(
        default="",
        description=(
            "Written first: 1-2 sentences on what the retrieved material contains "
            "and which branch below applies. Internal; never shown to the student."
        ),
    )
    link_response: str | None = Field(
        default=None,
        description=(
            "Set ONLY if a source contains a direct link to a quiz or exercise: a "
            "brief message pointing the student to it, including the URL as plain "
            "text. Leave null in every other case."
        ),
    )
    title: str = Field(default="", description="Short quiz title. Ignored if `link_response` is set.")
    subtitle: str = Field(default="", description="One-line quiz subtitle. Ignored if `link_response` is set.")
    questions: list[QuizQuestion] = Field(
        default_factory=list,
        description=(
            "Adapted from quiz/exercise content in the retrieved material if present, "
            "otherwise generated from the dialog history so far. Defaults to 5; follows "
            f"an explicit count the student asked for, up to {MAX_QUESTIONS}. "
            "Empty if `link_response` is set."
        ),
    )

    @model_validator(mode="after")
    def _clear_questions_if_link_response(self) -> Self:
        if self.link_response:
            self.questions = []
        return self

    @model_validator(mode="after")
    def _drop_unanswerable_questions(self) -> Self:
        answerable = [question for question in self.questions if question.is_answerable]
        if len(answerable) < len(self.questions):
            logger.warning(
                "Dropping %d unanswerable practice question(s)",
                len(self.questions) - len(answerable),
            )
            self.questions = answerable
        return self

    @model_validator(mode="after")
    def _cap_questions_at_max(self) -> Self:
        if len(self.questions) > self.MAX_QUESTIONS:
            logger.info(
                "Truncating practice questions from %d to %d",
                len(self.questions),
                self.MAX_QUESTIONS,
            )
            self.questions = self.questions[: self.MAX_QUESTIONS]
        return self


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
