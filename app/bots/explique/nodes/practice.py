import logging

from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.compilers import COMPILERS
from app.bots.explique.compilers.base import ExpliqueTask
from app.bots.explique.models import PracticeMaterial, QuizConfig, QuizQuestions
from app.bots.explique.quiz_page import Quiz
from app.bots.explique.state import ExpliqueBotState
from app.compilation.invoke import structured_call

logger = logging.getLogger(__name__)


async def practice_node(state: ExpliqueBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Compute this turn's practice material into `practice_response`, for `respond` to
    return verbatim when there is any."""
    bot = runtime.context
    material = await structured_call(
        bot=bot,
        compiler=COMPILERS.get(ExpliqueTask.PRACTICE),
        state=state,
        fallback=PracticeMaterial(),
    )

    if material.link_response:
        logger.info("Pointing the student to an existing practice link")
        return {"practice_response": material.link_response}

    if not material.questions:
        logger.warning("No practice material produced")
        return {"practice_response": None}

    quiz = Quiz(
        config=QuizConfig(course_name=bot.course_name, title=material.title, subtitle=material.subtitle),
        questions=QuizQuestions(questions=material.questions),
    )
    logger.info("Built a quiz with %d question(s)", len(material.questions))
    return {"practice_response": f"```html\n{quiz.render()}\n```"}
