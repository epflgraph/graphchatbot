import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import ClassVar

import jinja2
from pydantic import BaseModel

from app.bots.explique.models import QuizConfig, QuizQuestions
from app.logging_config import truncate

logger = logging.getLogger(__name__)

# Named for what it renders, not how it's built — `prompts/` next door is
# Jinja too, but for prompt text, not client-side markup.
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_NAME = "practice-quiz.html"


@lru_cache
def _environment() -> jinja2.Environment:
    """The page's own environment, separate from the one prompts render through:
    this output is markup for a browser, so escaping is on — every value the page
    interpolates is LLM-produced and must land as text, never as more markup."""
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ARTIFACTS_DIR)),
        autoescape=True,
        undefined=jinja2.StrictUndefined,
    )


class Quiz(BaseModel):
    # Bounds the embedded questions in a rendered page.
    QUESTIONS_START: ClassVar[str] = 'id="quiz-data">'
    QUESTIONS_END: ClassVar[str] = "</script>"

    config: QuizConfig
    questions: QuizQuestions

    def render(self) -> str:
        """The rendered quiz page. LLM-produced content reaches the
        template as data only — never as markup."""
        return (
            _environment()
            .get_template(ARTIFACT_NAME)
            .render(
                course_name=self.config.course_name,
                topic=self.config.title,
                subtitle=self.config.subtitle,
                questions=[question.model_dump() for question in self.questions.questions],
            )
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
