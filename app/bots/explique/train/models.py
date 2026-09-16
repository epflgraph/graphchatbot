import logging
from typing import ClassVar

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from app.bots.explique.models import QuizQuestion

logger = logging.getLogger(__name__)


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
