import logging

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from app.bots.base import Bot, StateUpdate
from app.bots.explique.grade.coverage_record import CoverageRecorder
from app.bots.explique.grade.prompts import (
    INVITE_PAST_DEADLINE_TEMPLATE,
    INVITE_TEMPLATE,
    INVITE_UNRECORDED_TEMPLATE,
    STATUS_ENROLMENT_TEMPLATE,
)
from app.bots.explique.grade.state import GradeBotState
from app.bots.utils import announce, stream_text
from app.compilation.templates import render_prompt

logger = logging.getLogger(__name__)


async def invite_node(state: GradeBotState, runtime: Runtime[Bot]) -> StateUpdate:
    """Ask for an explanation of the topic the student just picked."""
    bot = runtime.context
    topic = state["topic_lock"].topic
    template = INVITE_TEMPLATE
    recorder = CoverageRecorder(bot.course_id, state["requester"])
    if topic.is_past_deadline:
        # Nothing will be recorded, enrolled or not, so Moodle is not asked.
        logger.info("%r picked %r past its deadline; nothing will be recorded", recorder.requester_id, topic.name)
        template = INVITE_PAST_DEADLINE_TEMPLATE
    else:
        announce(STATUS_ENROLMENT_TEMPLATE, runtime)
        # `is False`, not `not`: only a definite no interrupts the exercise. A Moodle that
        # was not asked, or could not respond, says nothing about this student.
        if await recorder.is_student_enrolled() is False:
            logger.warning("Nothing will be recorded for %r.", recorder.requester_id)
            template = INVITE_UNRECORDED_TEMPLATE

    invitation = render_prompt(bot.prompt_search_path, template, topic=topic, lang_code=state.get("lang_code"))
    await stream_text(invitation, runtime.stream_writer)
    return {"messages": [AIMessage(content=invitation)]}
