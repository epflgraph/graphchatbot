import json
import logging
from pathlib import Path
from typing import Any, ClassVar, TypedDict

from langchain_core.messages import BaseMessage

from app.bots.artifacts.base import Artifact
from app.bots.explique.models import QuizConfig, QuizQuestions
from app.llms.utils import flatten_content
from app.logging_config import truncate

logger = logging.getLogger(__name__)


class QuizContext(TypedDict):
    course_name: str
    topic: str
    subtitle: str
    questions: list[dict[str, Any]]


class Quiz(Artifact):
    TEMPLATE_DIR: ClassVar[Path] = Path(__file__).parent / "artifacts"
    TEMPLATE_NAME: ClassVar[str] = "practice-quiz.html"
    QUESTIONS_START: ClassVar[str] = 'id="quiz-data">'
    QUESTIONS_END: ClassVar[str] = "</script>"

    config: QuizConfig
    questions: QuizQuestions

    def _context(self) -> QuizContext:
        return QuizContext(
            course_name=self.config.course_name,
            topic=self.config.title,
            subtitle=self.config.subtitle,
            questions=[question.model_dump() for question in self.questions.questions],
        )

    @staticmethod
    def find_questions(content: str) -> QuizQuestions | None:
        """The questions a rendered quiz page embeds.

        None means `content` isn't a quiz at all — leave it untouched. An
        empty `QuizQuestions` means it is a quiz, but its questions couldn't
        be read — still replace it, just with nothing to summarize.
        """
        start = content.find(Quiz.QUESTIONS_START)
        if start == -1:
            return None

        start += len(Quiz.QUESTIONS_START)
        end = content.find(Quiz.QUESTIONS_END, start)
        if end == -1:
            logger.debug("Embedded practice-quiz questions are cut off: no closing %r", Quiz.QUESTIONS_END)
            return QuizQuestions()

        try:
            return QuizQuestions(questions=json.loads(content[start:end]))
        except ValueError as error:
            logger.debug("Embedded practice-quiz questions did not validate: %s", truncate(error))
            return QuizQuestions()


def summarize_quiz(message: BaseMessage) -> BaseMessage:
    """Replace a rendered practice quiz with a summary of the questions it
    asked, leaving every other turn untouched."""
    if message.type != "ai":
        return message

    # Flatten first: content may be multi-part, and quiz markup needs one
    # string to match against.
    questions = Quiz.find_questions(flatten_content(message.content))
    if questions is None:
        return message

    # Copy rather than mutate: `messages` is graph state shared with the nodes
    # running in parallel on this turn.
    return message.model_copy(update={"content": questions.to_summary()})
