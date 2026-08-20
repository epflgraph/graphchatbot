import json
import logging
from pathlib import Path
from typing import Any, ClassVar, TypedDict

from app.bots.artifacts.base import Artifact
from app.bots.explique.models import QuizConfig, QuizQuestions
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
            return None

        try:
            return QuizQuestions(questions=json.loads(content[start:end]))
        except ValueError as error:
            logger.debug("Embedded practice-quiz questions did not validate: %s", truncate(error))
            return QuizQuestions()
