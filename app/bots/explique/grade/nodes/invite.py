import asyncio
import logging

from langchain_core.messages import AIMessage
from langgraph.constants import TAG_NOSTREAM
from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.compilers.respond import GradeOpeningQuestionCompiler
from app.bots.explique.grade.coverage_record import CoverageRecorder
from app.bots.explique.grade.prompts import (
    INVITE_PAST_DEADLINE_TEMPLATE,
    INVITE_QUESTION_TEMPLATE,
    INVITE_TEMPLATE,
    INVITE_UNRECORDED_TEMPLATE,
    STATUS_ENROLMENT_TEMPLATE,
)
from app.bots.explique.grade.state import GradeBotState
from app.bots.utils import announce, stream_text
from app.compilation.invoke import text_call
from app.compilation.templates import render_prompt

logger = logging.getLogger(__name__)


async def invite_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Ask for an explanation of the topic the student just picked, and put the first question to them."""
    bot = runtime.context
    lang_code = state.get("lang_code")
    # Written while Moodle is asked, so it adds no wait; without a question, the invitation stands alone.
    template, question = await asyncio.gather(
        _invite_template(state, runtime),
        text_call(
            bot,
            GradeOpeningQuestionCompiler,
            # For the invitation only, the templates fall back to English when no language is detected.
            {**state, "lang_code": lang_code or "en"},
            tags=(TAG_NOSTREAM,),
            fallback="",
        ),
    )

    invitation = render_prompt(bot.prompt_search_path, template, topic=state["topic_lock"].topic, lang_code=lang_code)
    if question := question.strip():
        opening = render_prompt(
            bot.prompt_search_path, INVITE_QUESTION_TEMPLATE, question=question, lang_code=lang_code
        )
        invitation = f"{invitation}\n\n{opening}"
    await stream_text(invitation, runtime.stream_writer)
    return {"messages": [AIMessage(content=invitation)]}


async def _invite_template(state: GradeBotState, runtime: Runtime[Bot]) -> str:
    """The invitation that fits this student: past the deadline, not enrolled, or the plain one."""
    bot = runtime.context
    topic = state["topic_lock"].topic
    recorder = CoverageRecorder(bot.course_id, state["requester"])
    if topic.is_past_deadline:
        # Nothing will be recorded, enrolled or not, so Moodle is not asked.
        logger.info("%r picked %r past its deadline; nothing will be recorded", recorder.requester_id, topic.name)
        return INVITE_PAST_DEADLINE_TEMPLATE

    announce(STATUS_ENROLMENT_TEMPLATE, runtime)
    # `is False`, not `not`: only a definite no interrupts the exercise. A Moodle that
    # was not asked, or could not respond, says nothing about this student.
    if await recorder.is_student_enrolled() is False:
        logger.warning("Nothing will be recorded for %r.", recorder.requester_id)
        return INVITE_UNRECORDED_TEMPLATE
    return INVITE_TEMPLATE
